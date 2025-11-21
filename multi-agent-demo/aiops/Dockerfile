FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

COPY ./requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install aws-opentelemetry-distro==0.10.1

RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080
EXPOSE 8000

COPY . /app/aiops

CMD ["opentelemetry-instrument", "python", "-m", "aiops.main"]
