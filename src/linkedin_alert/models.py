from dataclasses import dataclass


@dataclass(frozen=True)
class Job:
    linkedin_id: str
    title: str
    company: str
    location: str
    url: str
