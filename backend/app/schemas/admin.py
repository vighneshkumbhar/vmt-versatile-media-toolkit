from pydantic import BaseModel
class ReviewRequest(BaseModel):
    reason: str = ""
