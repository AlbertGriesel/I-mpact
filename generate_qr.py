"""
Promotional QR-code generator (spec §11).

This is an EXTERNAL asset tool — deliberately NOT wired into the running app
(the QR must not appear in the normal in-app interface). Run it from the
command line when the public deployment URL is known:

    python generate_qr.py https://your-public-site.example
    # or set IMPACT_PUBLIC_URL and run with no argument

It writes a high-resolution PNG and an SVG into ./promo/ with a generous quiet
zone and strong contrast, suitable for posters, slides and print.

Safety (spec §11 & §20):
  * refuses to generate for an empty / localhost / non-public URL — it will
    never produce a QR pointing at localhost.
  * uses `segno` (pure-python, no runtime dependency added to the app). If it
    isn't installed, the script tells you how to add it — the app itself never
    imports this file, so the dependency stays out of requirements.txt.
"""

import os
import sys

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "promo")
_BLOCKED_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0", "::1")


def _resolve_url(argv):
    if len(argv) > 1 and argv[1].strip():
        return argv[1].strip()
    return (os.environ.get("IMPACT_PUBLIC_URL") or "").strip()


def _validate(url):
    if not url:
        return False, ("No public URL provided. Pass it as an argument or set "
                       "IMPACT_PUBLIC_URL — e.g.\n"
                       "    python generate_qr.py https://impact.example.com")
    if not (url.startswith("http://") or url.startswith("https://")):
        return False, f"URL must start with http:// or https:// — got: {url!r}"
    host = url.split("://", 1)[1].split("/", 1)[0].split(":", 1)[0].lower()
    if any(host == b or host.startswith(b) for b in _BLOCKED_HOSTS):
        return False, (f"Refusing to make a QR for a local address ({host}). "
                       "Deploy the site and use its public URL first.")
    return True, url


def generate(url):
    try:
        import segno
    except ImportError:
        print("The 'segno' package is needed to render the QR (pure-python, no "
              "app dependency).\n    pip install segno\nthen re-run.",
              file=sys.stderr)
        return 2
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    qr = segno.make(url, error="h")   # high error-correction for print
    png_path = os.path.join(OUTPUT_DIR, "impact_qr.png")
    svg_path = os.path.join(OUTPUT_DIR, "impact_qr.svg")
    # scale 16 → high resolution; border 4 modules → adequate quiet zone
    qr.save(png_path, scale=16, border=4, dark="#0f2e1d", light="white")
    qr.save(svg_path, scale=16, border=4, dark="#0f2e1d", light="white")
    print(f"Wrote:\n  {png_path}\n  {svg_path}\nDestination: {url}\n"
          "Test the printed code with a couple of phones before distributing.")
    return 0


def main():
    ok, result = _validate(_resolve_url(sys.argv))
    if not ok:
        print(result, file=sys.stderr)
        return 1
    return generate(result)


if __name__ == "__main__":
    raise SystemExit(main())
