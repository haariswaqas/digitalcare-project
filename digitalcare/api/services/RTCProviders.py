import os
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VideoGrant

class TwilioProvider:
    def __init__(self):
        self.account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        self.api_key_sid = os.environ.get("TWILIO_API_KEY_SID")
        self.api_key_secret = os.environ.get("TWILIO_API_KEY_SECRET")
        # TTL in seconds
        self.ttl = int(os.environ.get("TWILIO_TOKEN_TTL", 3600))

    def create_room_name(self, consult):
        # simple deterministic room name; you can call Twilio REST API to create rooms too
        return f"consult-{consult.id}"

    def generate_token(self, identity: str, room: str, ttl: int | None = None) -> str:
        if ttl is None:
            ttl = self.ttl
        token = AccessToken(self.account_sid, self.api_key_sid, self.api_key_secret, identity=identity, ttl=ttl)
        grant = VideoGrant(room=room)
        token.add_grant(grant)
        # token.to_jwt() returns bytes in py3; decode to str
        return token.to_jwt()
