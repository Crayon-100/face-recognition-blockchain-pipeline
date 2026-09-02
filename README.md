# Face ID + Blockchain Verification Pipeline

A pipeline that detects a face in an input photo, performs a genuine reverse-image
search to find a real matching social media post, verifies that the match is
actually the same person via face comparison, and writes a tamper-evident record
of the match to the Ethereum Sepolia testnet.

Built for HH Goa Task #3 (Face ID + Blockchain Verification).

## What it does

1. **Face detection & encoding** — detects a face in the input image and converts
   it into a 128-dimension numerical encoding using the `face_recognition` library.
2. **Reverse image search** — uploads the image to SerpApi's Google Lens engine and
   retrieves visual matches from across the web. This is a live search against
   real results, not a hardcoded lookup.
3. **Match verification** — downloads each candidate image returned by the search,
   runs the same face encoding on it, and compares it against the original face
   using face-distance scoring. Results are ranked by similarity, and a
   confidence margin (gap between the best and second-best match) is reported
   alongside the raw distance, since a large margin is stronger evidence of a
   genuine match than a single threshold value alone.
4. **Blockchain recording** — once a verified match is found, a SHA-256 hash of
   the matched image plus its source URL is written to the Ethereum Sepolia
   testnet as transaction data. The record is then read back independently and
   re-hashed to confirm it matches exactly, demonstrating that the on-chain
   record is tamper-evident.

## Tech stack

- **Face detection/encoding:** [`face_recognition`](https://github.com/ageitgey/face_recognition) (built on dlib)
- **Reverse image search:** [SerpApi](https://serpapi.com/) — Google Lens engine
- **Blockchain:** Ethereum **Sepolia testnet**, via [`web3.py`](https://web3py.readthedocs.io/) and an [Alchemy](https://www.alchemy.com/) RPC endpoint
- **Runtime:** Google Colab

## Setup

This pipeline is designed to run in **Google Colab** and depends on Colab's
built-in Secrets manager for API keys and credentials. It will not run as a
plain local Python script without modification (see Limitations).

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

If `face_recognition` fails to install, it's almost always because its
dependency `dlib` needs `cmake` to compile. Run this first, then retry:

```bash
apt install cmake
pip install cmake dlib
```

### 2. Set up API keys and credentials

In Colab, click the 🔑 (key) icon in the left sidebar to open **Secrets**, and
add the following:

| Secret name | Value |
|---|---|
| `SerpApi` | Your SerpApi API key ([serpapi.com](https://serpapi.com/)) |
| `ETHkey` | Your Ethereum wallet's private key |
| `endpoint` | A Sepolia RPC URL (free tier from [Alchemy](https://www.alchemy.com/)) |

**Never commit these values, or your private key, to the repository.**

### 3. Fund your wallet with test ETH

The wallet corresponding to `ETHkey` needs a small amount of Sepolia test ETH
to pay gas fees. Get free test ETH from any public Sepolia faucet (e.g.
Alchemy's or Google Cloud's Sepolia faucet) by pasting in your wallet address.

### 4. Upload a test image

Upload a clear, front-facing photo to the Colab file panel, and update
`KNOWN_IMAGE_PATH` at the top of `pipeline.py` to match its filename.

**Only use a photo of yourself, or one you have explicit consent to use.**
Running facial recognition and reverse image search against someone else's
photo without their consent is not an appropriate use of this tool.

## How to run

Run the script's `main()` function (or execute `pipeline.py` as a single
Colab cell). It will:

1. Print the encoded face confirmation
2. Print the number of candidate matches found
3. Print the best match's URL, distance score, and confidence margin
4. Print the SHA-256 hash of the matched record
5. Print the Sepolia transaction link
6. Print whether the on-chain record was successfully re-verified

Example output:

```
Encoded face from test.jpg
Found 52 candidate matches
Best match: https://www.instagram.com/p/DaccXwQRYC2/ (distance: 0.1957)
Confidence margin over runner-up: 0.2766
Match record hash: da077ab2e5a6ff6ae2abfe74eaafb336de0d6c7fd3f7ff10a5af170113562...
Transaction sent: https://sepolia.etherscan.io/tx/13a42a05209903d35bb5cfa12eee0c35e2744...
VERIFIED: on-chain record matches the original match data.
```

## Blockchain used

**Ethereum Sepolia testnet.** A public testnet was chosen over mainnet since
this is a demonstration of the verification mechanism, not a production
system — testnet transactions are free (aside from faucet-provided test ETH)
and fully public/inspectable on [Sepolia Etherscan](https://sepolia.etherscan.io/),
while carrying no real monetary value or risk.

## Known limitations

- **Colab-dependent.** The script uses `google.colab.userdata` for secrets
  management, so it will not run outside a Colab environment without
  swapping this for another secrets/config method (e.g. environment
  variables).
- **Search quality depends on indexing.** Reverse image search can only find
  a match if the source photo has already been indexed by Google. Private
  accounts, very recent posts, or platforms that block search-engine
  crawling (Instagram in particular) may not surface a match even if the
  photo genuinely exists online.
- **Hotlink protection on some platforms.** Some sites (notably Instagram)
  block direct downloads of their hosted images. The pipeline falls back to
  Google's cached thumbnail in these cases, which is lower resolution and
  occasionally tightly cropped, which can affect face-detection accuracy on
  that specific candidate.
- **Threshold-based matching is not infallible.** A face-distance threshold
  of 0.45 was chosen based on testing, but face recognition is probabilistic,
  not exact. The confidence margin (gap between best and second-best result)
  is reported as an additional signal, but neither metric guarantees a
  perfect match in all cases, particularly with low-quality or heavily
  filtered candidate images.
- **Testnet, not mainnet.** The blockchain record is written to Sepolia, a
  free public testnet. It demonstrates the same tamper-evident mechanism as
  mainnet Ethereum, but the record has no real-world monetary backing.
- **Single face per image assumed.** The pipeline uses the first detected
  face encoding in both the known image and each candidate; images with
  multiple faces are not explicitly disambiguated.

## Disclaimer

This project is intended as a technical demonstration for a hackathon task.
It should only be used with images of oneself or with the explicit consent
of the person pictured. It is not intended for identifying or tracking
individuals without their knowledge or consent.
