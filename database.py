import hashlib
from datetime import datetime, timedelta
from pymongo import MongoClient


def _hash(answer: str) -> str:
    return hashlib.sha256(answer.lower().strip().encode()).hexdigest()


class CaptchaDatabase:
    def __init__(self, connection_string='mongodb://localhost:27017/',
                 db_name='video_captcha'):
        self.client = MongoClient(connection_string)
        self.db     = self.client[db_name]
        self.col    = self.db.active_captchas
        self._setup()

    def _setup(self):
        try:
            self.col.create_index("captcha_id", unique=True)
            self.col.create_index("expires_at", expireAfterSeconds=0)  # TTL index
            print("✅ MongoDB connected")
        except Exception as e:
            print(f"⚠️ MongoDB setup: {e}")

    def store_captcha(self, captcha_id, correct_answer, question_text,
                      expiry_minutes=5):
        try:
            self.col.insert_one({
                "captcha_id":  captcha_id,
                "answer_hash": _hash(correct_answer),
                "expires_at":  datetime.utcnow() + timedelta(minutes=expiry_minutes),
            })
            return True
        except Exception as e:
            print(f"Error storing CAPTCHA: {e}")
            return False

    def verify_captcha(self, captcha_id, user_answer):
        try:
            doc = self.col.find_one_and_delete({
                "captcha_id": captcha_id,
                "expires_at": {"$gt": datetime.utcnow()},
            })
            if not doc:
                return False, "CAPTCHA expired or not found"

            if _hash(user_answer) == doc["answer_hash"]:
                print(f"✅ Correct: {captcha_id}")
                return True, "Verification Successful!"
            else:
                print(f"❌ Wrong answer: {captcha_id}")
                return False, "Incorrect — Try Again"
        except Exception as e:
            print(f"Error verifying: {e}")
            return False, "Verification error"

    def cleanup_expired_captchas(self):
        # MongoDB TTL index handles this automatically.
        # Manual cleanup as fallback:
        try:
            r = self.col.delete_many({"expires_at": {"$lte": datetime.utcnow()}})
            if r.deleted_count:
                print(f"Cleaned {r.deleted_count} expired CAPTCHAs")
        except Exception as e:
            print(f"Cleanup error: {e}")

    def get_stats(self):
        try:
            return {"active_count": self.col.count_documents(
                {"expires_at": {"$gt": datetime.utcnow()}}
            )}
        except Exception:
            return {"active_count": 0}

    def test_connection(self):
        try:
            self.client.admin.command('ping')
            return True, "MongoDB connection successful"
        except Exception as e:
            return False, str(e)
