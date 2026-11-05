"""Native process containment for a cold boot.

The default is a new user and network namespace with no outbound route.
Network is shared with the parent only when ``authorize_network_allow``
returns a grant and that grant is passed into the launch. An environment
variable cannot select the allow path.

This package does not start a listener, place an order, or change the
public pin. The swarm study in ``aureon.swarm.containment`` is a different
module.
"""

from aureon.containment.native import (
    PIN,
    STARTED_FROM,
    ContainmentRefused,
    ContainmentUnavailable,
    NetworkAllowGrant,
    authorize_network_allow,
    prepare_launch,
)

__all__ = [
    "PIN",
    "STARTED_FROM",
    "ContainmentRefused",
    "ContainmentUnavailable",
    "NetworkAllowGrant",
    "authorize_network_allow",
    "prepare_launch",
]
