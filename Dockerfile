FROM ghcr.io/facebook/threatexchange/hma:1.1.0

# Set HMA config by default
ENV OMM_CONFIG=/matrix-config.py

# Install dos2unix because we have Windows users that build this thing
# We also install poetry in the same layer to make things a bit smaller
RUN apt-get update && apt-get install dos2unix -y && pip install poetry

# Install our custom extensions. We disable poetry's automatic venv creation
# because it'll make our code un-importable. Note that while the HMA Docker
# image uses `/app` by default, we don't really want to rely on that. Instead,
# we use relative commands.
#
# We also take this opportunity to move & prepare the startup scripts so we
# can save on layers.
COPY . .
RUN poetry config virtualenvs.create false  \
    && poetry install --without dev \
    && mv ./config.py /matrix-config.py \
    && mv ./startup.sh /matrix-startup.sh \
    && dos2unix /matrix-startup.sh \
    && chmod +x /matrix-startup.sh

CMD ["/matrix-startup.sh"]
