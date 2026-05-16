import uuid
from typing import Any

from pydantic import BaseModel, Field, field_validator


def ensure_unique_id(v: Any) -> str:
    """Ensure the ID is a valid, unique UUID and not a placeholder."""
    PLACEHOLDER_ID = "4f4e4f4e-4f4e-4f4e-4f4e-4f4e4f4e4f4e"
    if not v or v == "uuid" or v == PLACEHOLDER_ID:
        return str(uuid.uuid4())
    return str(v)


def coerce_date_to_string(v: Any) -> str:
    """Coerce various date formats (strings, dicts) into a single string."""
    if isinstance(v, dict):
        # Handle cases like {'active': '...', 'expiration': '...'} or {'start': '...', 'end': '...'}
        parts = []
        for key, value in v.items():
            if value:
                parts.append(f"{key.capitalize()}: {value}")
        return " | ".join(parts)
    if v is None:
        return ""
    return str(v)


class BaseItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, v: Any) -> str:
        return ensure_unique_id(v)


class Website(BaseModel):
    label: str = ""
    href: str = ""


class CustomField(BaseItem):
    icon: str = ""
    text: str = ""
    link: str = ""


class Picture(BaseModel):
    url: str = ""
    size: int = 64
    aspectRatio: int = 1
    borderRadius: int = 0
    borderColor: str = "#000000"
    borderWidth: int = 0
    shadowColor: str = "#000000"
    shadowWidth: int = 0


class Basics(BaseModel):
    name: str = ""
    headline: str = ""
    email: str = ""
    phone: str = ""
    countryCode: str = ""
    location: str = ""
    url: Website = Field(default_factory=Website)
    customFields: list[CustomField] = []


class Summary(BaseModel):
    visible: bool = True
    content: str = ""


class SectionBase(BaseModel):
    name: str
    visible: bool = True
    columns: int = 1
    separate: bool = False


class EducationItem(BaseItem):
    school: str = ""
    degree: str = ""
    area: str = ""
    grade: str = ""
    location: str = ""
    period: str = ""
    website: Website = Field(default_factory=Website)
    description: str = ""
    visible: bool = True

    @field_validator("period", mode="before")
    @classmethod
    def validate_period(cls, v: Any) -> str:
        return coerce_date_to_string(v)


class ExperienceRole(BaseItem):
    position: str = ""
    period: str = ""
    description: str = ""

    @field_validator("period", mode="before")
    @classmethod
    def validate_period(cls, v: Any) -> str:
        return coerce_date_to_string(v)


class ExperienceItem(BaseItem):
    company: str = ""
    position: str = ""
    location: str = ""
    period: str = ""
    website: Website = Field(default_factory=Website)
    description: str = ""
    roles: list[ExperienceRole] = []
    visible: bool = True

    @field_validator("period", mode="before")
    @classmethod
    def validate_period(cls, v: Any) -> str:
        return coerce_date_to_string(v)


class ProjectItem(BaseItem):
    name: str = ""
    description: str = ""
    period: str = ""
    website: Website = Field(default_factory=Website)
    keywords: list[str] = []
    visible: bool = True

    @field_validator("period", mode="before")
    @classmethod
    def validate_period(cls, v: Any) -> str:
        return coerce_date_to_string(v)


class SkillItem(BaseItem):
    name: str = ""
    description: str = ""
    level: int = 0
    keywords: list[str] = []
    visible: bool = True


class ProfileItem(BaseItem):
    network: str = ""
    username: str = ""
    icon: str = ""
    website: Website = Field(default_factory=Website)
    visible: bool = True


class LanguageItem(BaseItem):
    name: str = ""
    description: str = ""
    level: int = 0
    visible: bool = True


class InterestItem(BaseItem):
    name: str = ""
    keywords: list[str] = []
    visible: bool = True


class AwardItem(BaseItem):
    title: str = ""
    awarder: str = ""
    date: str = ""
    description: str = ""
    visible: bool = True

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, v: Any) -> str:
        return coerce_date_to_string(v)


class CertificationItem(BaseItem):
    name: str = ""
    issuer: str = ""
    date: str = ""
    description: str = ""
    website: Website = Field(default_factory=Website)
    visible: bool = True

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, v: Any) -> str:
        return coerce_date_to_string(v)


class PublicationItem(BaseItem):
    name: str = ""
    publisher: str = ""
    date: str = ""
    description: str = ""
    website: Website = Field(default_factory=Website)
    visible: bool = True

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, v: Any) -> str:
        return coerce_date_to_string(v)


class VolunteerItem(BaseItem):
    organization: str = ""
    position: str = ""
    location: str = ""
    period: str = ""
    website: Website = Field(default_factory=Website)
    description: str = ""
    visible: bool = True

    @field_validator("period", mode="before")
    @classmethod
    def validate_period(cls, v: Any) -> str:
        return coerce_date_to_string(v)


class ReferenceItem(BaseItem):
    name: str = ""
    position: str = ""
    phone: str = ""
    email: str = ""
    description: str = ""
    visible: bool = True


class SectionProfiles(SectionBase):
    items: list[ProfileItem] = []


class SectionExperience(SectionBase):
    items: list[ExperienceItem] = []


class SectionEducation(SectionBase):
    items: list[EducationItem] = []


class SectionProjects(SectionBase):
    items: list[ProjectItem] = []


class SectionSkills(SectionBase):
    items: list[SkillItem] = []


class SectionLanguages(SectionBase):
    items: list[LanguageItem] = []


class SectionInterests(SectionBase):
    items: list[InterestItem] = []


class SectionAwards(SectionBase):
    items: list[AwardItem] = []


class SectionCertifications(SectionBase):
    items: list[CertificationItem] = []


class SectionPublications(SectionBase):
    items: list[PublicationItem] = []


class SectionVolunteer(SectionBase):
    items: list[VolunteerItem] = []


class SectionReferences(SectionBase):
    items: list[ReferenceItem] = []


class Sections(BaseModel):
    profiles: SectionProfiles = Field(default_factory=lambda: SectionProfiles(name="Profiles"))
    experience: SectionExperience = Field(
        default_factory=lambda: SectionExperience(name="Experience")
    )
    education: SectionEducation = Field(default_factory=lambda: SectionEducation(name="Education"))
    projects: SectionProjects = Field(default_factory=lambda: SectionProjects(name="Projects"))
    skills: SectionSkills = Field(default_factory=lambda: SectionSkills(name="Skills"))
    languages: SectionLanguages = Field(default_factory=lambda: SectionLanguages(name="Languages"))
    interests: SectionInterests = Field(default_factory=lambda: SectionInterests(name="Interests"))
    awards: SectionAwards = Field(default_factory=lambda: SectionAwards(name="Awards"))
    certifications: SectionCertifications = Field(
        default_factory=lambda: SectionCertifications(name="Certifications")
    )
    publications: SectionPublications = Field(
        default_factory=lambda: SectionPublications(name="Publications")
    )
    volunteer: SectionVolunteer = Field(default_factory=lambda: SectionVolunteer(name="Volunteer"))
    references: SectionReferences = Field(
        default_factory=lambda: SectionReferences(name="References")
    )


class CustomSection(SectionBase, BaseItem):
    items: list[dict] = []


class ResumeMetadataLayoutPage(BaseModel):
    main: list[str] = ["summary", "experience", "education", "projects"]
    sidebar: list[str] = ["skills", "profiles"]


class ResumeMetadataLayout(BaseModel):
    pages: list[ResumeMetadataLayoutPage] = Field(
        default_factory=lambda: [ResumeMetadataLayoutPage()]
    )


class ResumeMetadataTypography(BaseModel):
    fontFamily: str = "Open Sans"
    fontSize: int = 11


class ResumeMetadataTheme(BaseModel):
    primary: str = "#1f2937"


class ResumeMetadata(BaseModel):
    template: str = "onyx"
    layout: ResumeMetadataLayout = Field(default_factory=ResumeMetadataLayout)
    typography: ResumeMetadataTypography = Field(default_factory=ResumeMetadataTypography)
    theme: ResumeMetadataTheme = Field(default_factory=ResumeMetadataTheme)


class ResumeData(BaseModel):
    """Complete resume data structure matching frontend types."""

    picture: Picture = Field(default_factory=Picture)
    basics: Basics = Field(default_factory=Basics)
    summary: Summary = Field(default_factory=Summary)
    sections: Sections = Field(default_factory=Sections)
    customSections: list[CustomSection] = []
    metadata: ResumeMetadata = Field(default_factory=ResumeMetadata)
