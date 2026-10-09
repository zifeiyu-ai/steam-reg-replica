import random
import string


def generate_random_string(length):
    chars = string.digits + string.ascii_lowercase + string.ascii_uppercase
    return ''.join(random.choice(chars) for _ in range(length))


def generate_random_string2(length):
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    parts = [
        random.choice(lower),
        random.choice(upper),
        random.choice(digits),
    ]
    remaining = length - len(parts)
    pool = lower + upper + digits
    parts.extend(random.choice(pool) for _ in range(max(0, remaining)))
    random.shuffle(parts)
    return ''.join(parts[:length])


def parse_email_line(line):
    line = line.strip()
    if not line:
        return None
    parts = line.split('----')
    if len(parts) < 2:
        return None
    info = {'email': parts[0].strip(), 'password': parts[1].strip()}
    if len(parts) >= 4 and parts[2].strip() and parts[3].strip():
        info['client_id'] = parts[2].strip()
        info['refresh_token'] = parts[3].strip()
    elif len(parts) >= 3 and parts[2].strip():
        info['refresh_token'] = parts[2].strip()
    return info
