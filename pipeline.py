"""
Face ID + Blockchain Verification Pipeline

Detects a face in an input image, performs a genuine reverse-image search
to find a real matching social media post, verifies the match via face
comparison, and writes a tamper-evident record of the match to the
Ethereum Sepolia testnet.

Requires the following to be set in Colab Secrets (or environment variables
if run outside Colab):
    SerpApi  - SerpApi API key
    ETHkey   - Ethereum wallet private key (Sepolia testnet)
    endpoint - Sepolia RPC endpoint URL (e.g. from Alchemy)
"""

import hashlib

import face_recognition
import requests
import serpapi
from google.colab import userdata
from web3 import Web3

KNOWN_IMAGE_PATH = "test.jpg"
MATCH_THRESHOLD = 0.45
SEPOLIA_CHAIN_ID = 11155111
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.google.com/",
}


def encode_known_face(image_path):
    image = face_recognition.load_image_file(image_path)
    return face_recognition.face_encodings(image)[0]


def search_visual_matches(image_path, api_key):
    client = serpapi.Client(api_key=api_key)
    upload = client.upload_image(image_path)
    results = client.search({
        "engine": "google_lens",
        "image_id": upload["image_id"],
    })
    return results.get("visual_matches", [])


def download_candidate(match, index):
    for field in ("image", "thumbnail"):
        url = match.get(field)
        if not url:
            continue
        try:
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
            content_type = response.headers.get("Content-Type", "")
            if response.status_code == 200 and "image" in content_type:
                path = f"candidate_{index}.jpg"
                with open(path, "wb") as f:
                    f.write(response.content)
                return path
        except requests.RequestException:
            continue
    return None


def find_best_match(visual_matches, known_encoding):
    scored = []

    for i, match in enumerate(visual_matches):
        candidate_path = download_candidate(match, i)
        if not candidate_path:
            continue

        candidate_image = face_recognition.load_image_file(candidate_path)
        candidate_encodings = face_recognition.face_encodings(candidate_image)
        if not candidate_encodings:
            continue

        distance = face_recognition.face_distance([known_encoding], candidate_encodings[0])[0]
        scored.append((distance, match.get("link"), candidate_path))

    scored.sort(key=lambda x: x[0])
    return scored


def hash_match_record(image_path, matched_url):
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    combined = image_bytes + matched_url.encode()
    return hashlib.sha256(combined).hexdigest(), combined


def write_record_to_chain(w3, account, private_key, record_hash):
    tx = {
        "from": account.address,
        "to": account.address,
        "value": 0,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 100000,
        "gasPrice": w3.eth.gas_price,
        "data": w3.to_bytes(hexstr=record_hash),
        "chainId": SEPOLIA_CHAIN_ID,
    }
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash


def verify_onchain_record(w3, tx_hash, expected_hash):
    onchain_tx = w3.eth.get_transaction(tx_hash)
    onchain_data = onchain_tx["input"].hex().replace("0x", "")
    return onchain_data == expected_hash


def main():
    serpapi_key = userdata.get("SerpApi")
    private_key = userdata.get("ETHkey")
    rpc_endpoint = userdata.get("endpoint")

    known_encoding = encode_known_face(KNOWN_IMAGE_PATH)
    print(f"Encoded face from {KNOWN_IMAGE_PATH}")

    visual_matches = search_visual_matches(KNOWN_IMAGE_PATH, serpapi_key)
    print(f"Found {len(visual_matches)} candidate matches")

    ranked = find_best_match(visual_matches, known_encoding)
    if not ranked:
        print("No verified matches found among candidates.")
        return

    best_distance, best_link, best_image_path = ranked[0]
    print(f"Best match: {best_link} (distance: {best_distance:.4f})")

    if best_distance > MATCH_THRESHOLD:
        print("Best candidate did not meet the confidence threshold.")
        return

    if len(ranked) > 1:
        margin = ranked[1][0] - best_distance
        print(f"Confidence margin over runner-up: {margin:.4f}")

    record_hash, _ = hash_match_record(best_image_path, best_link)
    print(f"Match record hash: {record_hash}")

    w3 = Web3(Web3.HTTPProvider(rpc_endpoint))
    account = w3.eth.account.from_key(private_key)

    tx_hash = write_record_to_chain(w3, account, private_key, record_hash)
    print(f"Transaction sent: https://sepolia.etherscan.io/tx/{tx_hash.hex()}")

    if verify_onchain_record(w3, tx_hash, record_hash):
        print("VERIFIED: on-chain record matches the original match data.")
    else:
        print("WARNING: on-chain record does not match expected hash.")


if __name__ == "__main__":
    main()