# GPLv3 versus AGPLv3 decision record

**Owner decision: AGPLv3-or-later.** This document preserves the practical
comparison that informed the decision. It is not legal advice.

Milestone 6.20B records the decision but intentionally does not add `LICENSE`.
Applying the license, contribution terms, and public repository identity remains
part of the later public identity milestone.

Authoritative references:

- [GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.html)
- [GNU AGPLv3](https://www.gnu.org/licenses/agpl-3.0.html)
- [GNU explanation of the AGPL network provision](https://www.gnu.org/licenses/why-affero-gpl.html)

## Practical comparison

| Project use | GPLv3 | AGPLv3 |
| --- | --- | --- |
| Windows desktop installer | Strong copyleft applies when covered binaries or modified versions are conveyed. Corresponding source must accompany public distribution through an allowed method. | Largely the same result for a locally installed desktop application. |
| Linux/headless package | Strong copyleft applies when copies are conveyed. Running an unmodified or modified private instance without conveying it generally does not itself trigger source delivery. | Adds obligations when users interact remotely with a modified covered program over a network: those users must be offered corresponding source. |
| Future hosted/remote monitor | A third party may operate a modified hosted service without distributing a copy and therefore may avoid GPL source-distribution obligations. | Designed to close that network-service gap and require a source offer to remote users of the modified service. |
| iPhone companion | Distribution remains subject to copyleft and app-store terms. Compatibility with a store's terms and technical restrictions needs specific review under either license. | Same store review is needed, plus the network-source obligation if the companion or backend is modified and network-interactive. |
| Outside contributions | Contributions are normally received under the chosen project license unless a separate contributor agreement says otherwise. | Same, with contributors accepting the additional network-use condition. Some organizations may be less willing to adopt or contribute to AGPL software. |
| Donation-supported model | Compatible; the license permits charging for distribution/support even if the project chooses to remain free. Donations do not weaken copyleft. | Same. |

## Relicensing flexibility

The original copyright owner can relicense code they solely own. Once outside
contributions are accepted, changing the license generally requires permission
from all relevant copyright holders unless contributor terms grant broader
rights. The project currently has no contributor license agreement and should
decide whether simple inbound-equals-outbound contribution terms are sufficient
before accepting contributions.

## Decision rationale

- **GPLv3** would prioritize reciprocal source availability for
  distributed desktop/Linux binaries and lower adoption friction for users who
  may avoid AGPL dependencies.
- **AGPLv3** also preserves source access for a future modified hosted or
  remotely accessible monitor, which matches the selected direction.

The owner selected the `-or-later` formulation. No `LICENSE` file is added in
this milestone.
