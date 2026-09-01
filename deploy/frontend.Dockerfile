# Aureon frontend release image: terminal native/container HOLD.
# No package lifecycle, target source, listener, health probe, or network tooling is
# executed before the boundary. A separately attested build phase is required
# before any frontend artifact can be included in a release image.
FROM alpine:3.21

WORKDIR /opt/aureon
COPY scripts/bootstrap/frontend_container_hold_v05.sh /opt/aureon/scripts/bootstrap/frontend_container_hold_v05.sh

USER 65532:65532
ENTRYPOINT ["/bin/sh", "/opt/aureon/scripts/bootstrap/frontend_container_hold_v05.sh"]
CMD []
