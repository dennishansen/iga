#!/usr/bin/env python3
"""
Ko-fi webhook receiver for payment notifications.

Ko-fi sends POST requests with payment data when someone donates.
The data comes as form-encoded with a 'data' field containing JSON.

Files used:
- data/kofi_payments.json: Log of all payments received
- data/kofi_token.txt: Verification token (optional)
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, jsonify

app = Flask(__name__)

# File paths
DATA_DIR = Path(__file__).parent.parent / "data"
PAYMENTS_FILE = DATA_DIR / "kofi_payments.json"
TOKEN_FILE = DATA_DIR / "kofi_token.txt"


def get_verification_token():
    """Get Ko-fi verification token."""
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    return os.getenv('KOFI_VERIFICATION_TOKEN')


def load_payments():
    """Load payments log from file."""
    if PAYMENTS_FILE.exists():
        try:
            data = json.loads(PAYMENTS_FILE.read_text())
            # Handle both list format and dict format
            if isinstance(data, list):
                return {"payments": data}
            return data
        except json.JSONDecodeError:
            pass
    return {"payments": []}


def save_payments(data):
    """Save payments log to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PAYMENTS_FILE.write_text(json.dumps(data, indent=2))


def extract_telegram_username(message):
    """Extract @username from message if present."""
    if not message:
        return None
    match = re.search(r'@([a-zA-Z0-9_]{5,32})', message)
    return match.group(1) if match else None


@app.route('/kofi', methods=['POST'])
def kofi_webhook():
    """Receive Ko-fi webhook notifications."""
    data_str = request.form.get('data')
    if not data_str:
        return jsonify({'error': 'No data'}), 400

    try:
        payload = json.loads(data_str)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON'}), 400

    # Verify token if configured
    expected_token = get_verification_token()
    if expected_token and payload.get('verification_token') != expected_token:
        print("[Ko-fi] Invalid verification token")
        return jsonify({'error': 'Invalid token'}), 403

    # Extract payment info
    payment = {
        'timestamp': datetime.now().isoformat(),
        'message_id': payload.get('message_id'),
        'kofi_transaction_id': payload.get('kofi_transaction_id'),
        'type': payload.get('type'),
        'from_name': payload.get('from_name'),
        'email': payload.get('email'),
        'amount': payload.get('amount'),
        'currency': payload.get('currency', 'USD'),
        'message': payload.get('message'),
        'is_public': payload.get('is_public', False),
        'telegram_username': extract_telegram_username(payload.get('message'))
    }

    # Load and check for duplicates
    payments_data = load_payments()
    existing_ids = {p.get('message_id') for p in payments_data['payments'] if p.get('message_id')}

    if payment['message_id'] and payment['message_id'] in existing_ids:
        print(f"[Ko-fi] Duplicate webhook ignored: {payment['message_id']}")
        return jsonify({'success': True, 'duplicate': True})

    # Save payment
    payments_data['payments'].append(payment)
    save_payments(payments_data)

    # Print to console
    print(f"\n[Ko-fi] Payment received!")
    print(f"  From: {payment['from_name']}")
    print(f"  Amount: {payment['amount']} {payment['currency']}")
    print(f"  Type: {payment['type']}")
    if payment['message']:
        print(f"  Message: {payment['message']}")
    if payment['telegram_username']:
        print(f"  Telegram: @{payment['telegram_username']}")

    return jsonify({'success': True})


def has_paid_recently(telegram_username, days=30):
    """
    Check if a Telegram username has made a payment recently.

    Args:
        telegram_username: Username to check (with or without @)
        days: How many days to look back (default 30)

    Returns:
        dict with 'paid' (bool) and payment details if found
    """
    if telegram_username.startswith('@'):
        telegram_username = telegram_username[1:]
    telegram_username = telegram_username.lower()

    cutoff = datetime.now() - timedelta(days=days)
    payments_data = load_payments()

    for payment in reversed(payments_data['payments']):
        stored_username = payment.get('telegram_username', '')
        if stored_username and stored_username.lower() == telegram_username:
            payment_time = datetime.fromisoformat(payment['timestamp'])
            if payment_time >= cutoff:
                return {
                    'paid': True,
                    'amount': payment['amount'],
                    'currency': payment.get('currency', 'USD'),
                    'timestamp': payment['timestamp'],
                    'from_name': payment['from_name']
                }

    return {'paid': False}


def get_recent_payments(days=7):
    """Get all payments from the last N days."""
    cutoff = datetime.now() - timedelta(days=days)
    payments_data = load_payments()

    recent = []
    for payment in payments_data['payments']:
        payment_time = datetime.fromisoformat(payment['timestamp'])
        if payment_time >= cutoff:
            recent.append(payment)
    return recent


if __name__ == '__main__':
    print("[Ko-fi] Starting webhook server on port 5001...")
    print("[Ko-fi] Endpoint: POST /kofi")
    app.run(host='0.0.0.0', port=5001)
