"""Copy only explicitly public configuration into the frontend's local environment."""
from pathlib import Path
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
source = root / '.env'
if source.exists():
    values = dotenv_values(source)
    keys = ('NEXT_PUBLIC_API_URL', 'NEXT_PUBLIC_REGISTRY_ADDRESS', 'NEXT_PUBLIC_ESCROW_ADDRESS')
    lines = [f'{key}={values[key]}' for key in keys if values.get(key)]
    (root / 'web/.env.local').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('Public frontend variables synchronized; no private variables copied.')
else:
    print('No .env found. Frontend can run with the network unavailable.')
