from pydantic import BaseModel
from typing import Optional


class PersonalInfo(BaseModel):
    """Personal information section of a resume."""
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: Optional[str] = ""
    website: Optional[str] = ""
    github: Optional[str] = ""
    summary: str = ""


class Education(BaseModel):
    """Education entry in a resume."""
    id: str
    school: str = ""
    degree: str = ""
    field: str = ""
    startDate: str = ""
    endDate: str = ""
    gpa: Optional[str] = ""
    description: str = ""


class WorkExperience(BaseModel):
    """Work experience entry in a resume."""
    id: str
    company: str = ""
    position: str = ""
    location: str = ""
    startDate: str = ""
    endDate: str = ""
    current: bool = False
    description: str = ""


class Project(BaseModel):
    """Project entry in a resume."""
    id: str
    name: str = ""
    technologies: str = ""
    startDate: str = ""
    endDate: str = ""
    description: str = ""
    link: Optional[str] = ""


class Skill(BaseModel):
    """Skill category in a resume."""
    id: str
    category: str = ""
    items: str = ""


class ResumeData(BaseModel):
    """Complete resume data structure matching frontend types."""
    personalInfo: PersonalInfo
    education: list[Education] = []
    workExperience: list[WorkExperience] = []
    projects: list[Project] = []
    skills: list[Skill] = []
    customSections: list = []
