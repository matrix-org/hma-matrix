FROM ghcr.io/facebook/threatexchange/hma:1.1.0

# Install dos2unix because we have Windows users that build this thing
RUN apt-get update && apt-get install dos2unix -y

# Set HMA config by default
ENV OMM_CONFIG=/matrix-config.py

COPY ./config.py /matrix-config.py
COPY ./startup.sh /matrix-startup.sh

RUN dos2unix /matrix-startup.sh && chmod +x /matrix-startup.sh

CMD ["/matrix-startup.sh"]
