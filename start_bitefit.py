"""
BiteFit launcher — shows phone URL + QR code, then starts Streamlit.
Run from the nutrition-app directory:
    python start_bitefit.py
"""

import socket
import subprocess
import sys
import os

PORT = 8501

# ── Detect all useful IPv4 addresses ─────────────────────────────────────────
def get_ips():
    ips = {}
    try:
        import subprocess as sp
        out = sp.check_output("ipconfig", shell=True, text=True, errors="replace")
        current_adapter = ""
        current_ip = None
        for line in out.splitlines():
            line_s = line.strip()
            if line_s and not line_s.startswith(" ") and "adapter" in line.lower():
                if current_ip:
                    ips[current_adapter] = current_ip
                    current_ip = None
                current_adapter = line_s.replace(":", "").strip()
            if "IPv4" in line and "10." in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    current_ip = parts[-1].strip()
            elif "IPv4" in line and "172." in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    current_ip = parts[-1].strip()
            elif "IPv4" in line and "192.168" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    current_ip = parts[-1].strip()
            # Tailscale
            elif "IPv4" in line and "100." in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    ip = parts[-1].strip()
                    ips["Tailscale (stable)"] = ip
        if current_ip:
            ips[current_adapter] = current_ip
    except Exception:
        pass

    # Fallback: socket trick
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips["Wi-Fi"] = s.getsockname()[0]
            s.close()
        except Exception:
            pass

    return ips


# ── Print QR code in terminal ─────────────────────────────────────────────────
def print_qr(url: str):
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except ImportError:
        pass


# ── Firewall: ensure rule exists ──────────────────────────────────────────────
def ensure_firewall():
    import subprocess
    result = subprocess.run(
        f'netsh advfirewall firewall show rule name="BiteFit {PORT}"',
        shell=True, capture_output=True, text=True
    )
    if "No rules match" in result.stdout or result.returncode != 0:
        print("  Adding firewall rule...")
        subprocess.run(
            f'netsh advfirewall firewall add rule name="BiteFit {PORT}" '
            f'dir=in action=allow protocol=TCP localport={PORT}',
            shell=True, capture_output=True
        )
        print("  Firewall rule added.")
    else:
        print("  Firewall rule OK.")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("\n" + "=" * 55)
    print("  🍏  BiteFit — Starting up")
    print("=" * 55)

    # Firewall
    print("\n📡 Network:")
    ensure_firewall()

    # IPs
    ips = get_ips()
    if not ips:
        print("  ⚠️  Could not detect IP address.")
    else:
        print()
        best_url = None
        for adapter, ip in ips.items():
            url = f"http://{ip}:{PORT}"
            label = "📱 Phone URL"
            if "Tailscale" in adapter:
                label = "🔒 Tailscale (works on ANY network)"
            print(f"  {label}:  {url}")
            if not best_url or "Tailscale" in adapter:
                best_url = url

        # Show QR for best URL
        if best_url:
            print(f"\n  📷 Scan this QR code from your phone:\n")
            print_qr(best_url)
            print(f"\n  URL: {best_url}")

    print("\n" + "=" * 55)
    print("  Starting Streamlit... (Ctrl+C to stop)")
    print("=" * 55 + "\n")

    # Start streamlit
    python = sys.executable
    app_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_user.py")
    subprocess.run([python, "-m", "streamlit", "run", app_file,
                    "--server.port", str(PORT),
                    "--server.address", "0.0.0.0",
                    "--server.headless", "true"])


if __name__ == "__main__":
    main()
