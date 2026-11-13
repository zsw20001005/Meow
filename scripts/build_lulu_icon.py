"""Export the existing idle character as a multi-resolution Windows icon."""
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[1]
source = root / 'windows/Meow.Windows/Assets/Lulu/Video/hd-idle-0.png'
frame = Image.open(source).convert('RGBA').crop((0, 0, 512, 512))
character = frame.crop(frame.getbbox())
character.thumbnail((232, 232), Image.Resampling.LANCZOS)
icon = Image.new('RGBA', (256, 256))
icon.alpha_composite(character, ((256-character.width)//2, (256-character.height)//2))
target = root / 'windows/Meow.Windows/Assets/Lulu.ico'
icon.save(target, sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
preview = root / 'build/installer-dependencies/Lulu-icon.png'
preview.parent.mkdir(parents=True, exist_ok=True)
icon.save(preview)
print(target)
