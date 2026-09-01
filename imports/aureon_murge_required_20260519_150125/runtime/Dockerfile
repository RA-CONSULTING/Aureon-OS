FROM gcc:14-bookworm AS hold-builder

RUN printf '%s\n' 'int main(void) { return 2; }' > /tmp/terminal_hold.c \
    && cc -Os -static -s -o /terminal-hold /tmp/terminal_hold.c

FROM scratch

COPY --from=hold-builder --chown=65532:65532 /terminal-hold /terminal-hold
USER 65532:65532
ENTRYPOINT ["/terminal-hold"]
