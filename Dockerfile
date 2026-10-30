FROM python:3.11-slim

ARG DIFFICULTAI_BUILD_SHA=unverified

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SCORECARD_DIR=/data/scorecards \
    DIFFICULTAI_BUILD_SHA=$DIFFICULTAI_BUILD_SHA

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 difficultai \
    && mkdir -p /data/scorecards \
    && chown difficultai:difficultai /data/scorecards

COPY --chown=difficultai:difficultai . .

USER difficultai

CMD ["python", "-m", "apps.livekit_agent", "start"]
