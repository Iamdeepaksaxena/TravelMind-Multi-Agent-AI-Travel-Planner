from setuptools import setup,find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="MULTI-AI AGENT",
    version="0.1",
    author="Deepak",
    packages=find_packages(),
    install_requires = requirements,
)

postgresql://agentdatabase:wWTxTRaWQj1DrOGYPCeDJVZ59OqH69Sp@dpg-d9c9sr7lk1mc739hdrb0-a.oregon-postgres.render.com/deepakkumar