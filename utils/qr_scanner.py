from pathlib import Path
import qrcode

def generate_qr(data: str, output_path: str):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img = qrcode.make(data)
    img.save(output_path)
    return output_path
