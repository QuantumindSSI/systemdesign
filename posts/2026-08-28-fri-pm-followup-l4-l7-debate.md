# Week 1 · Fri 2026-08-28 · Short follow-up: Who Should Be Allowed to Read the Request?

> Calendar row: W1 Fri PM, 17:00. Format: debate prompt. Pillar: System
> Design Fundamentals. Pass: Foundations. Builds on this morning's essay,
> `posts/2026-08-28-fri-am-essay-l4-l7-load-balancing.md`.
>
> Adversarial review record (2026-08-28): the positions below are explicit
> engineering archetypes, not invented people or attributed production
> stories. Each position is grounded in capabilities documented by Google
> Cloud, AWS, Envoy, and RFC 9110 and cited in the morning essay. No claim or
> measurement from Thursday's algorithm tutorial is reused. Zero em dashes.

---

**Topic:** A structured argument over whether application policy belongs at an L7 load balancer or inside each service

**Subtitle:** Both boundaries can protect a system and both can widen the wrong failure, so the deciding factor is which team and component you trust with protocol authority.

This morning, we replaced "L4 is fast, L7 is smart" with a harder question: where should traffic change ownership? Now let us make the two strongest teams defend opposite answers.

Neither position below is a fictional war story. They are two real design philosophies, tested against the same hypothetical public API. The API carries account and checkout traffic, needs TLS, and is maintained by several service teams.

## Position A: centralize application policy at the L7 boundary

The platform team's case starts with consistency. Let one application-aware proxy terminate the client connection, authenticate the caller, sanitize headers, assign a request ID, apply route-level timeouts, and produce one access-log shape before traffic reaches any service.

The mechanism is concrete. An L7 proxy decodes HTTP into headers, body data, and trailers. Products such as AWS Application Load Balancer can route on hosts, paths, methods, headers, and query parameters. Envoy can apply HTTP filters, tracing, retries, and route policy. The backend hop can still use HTTPS, so central inspection does not require plaintext traffic across the rest of the network.

The strongest scenario for this side is a security fix. If a dangerous header must be stripped or one route must be blocked now, changing a single managed boundary is faster and more consistent than waiting for every service team to implement the rule correctly. The same control point also gives incident responders request-level status, route, and tracing data.

Its risk is equally concentrated. A bad authentication rule, route mutation, retry policy, or certificate rollout can affect every service behind the proxy. Central consistency means central blast radius.

## Position B: keep traffic opaque until the service

The service team's case starts with authority. The component that understands an operation should decide how to authenticate it, whether it is safe to retry, and which details may be logged. A transport boundary should move traffic and perform health checks without quietly becoming a second application runtime.

The strongest scenario for this side is end-to-end client authentication or a protocol the shared proxy should not interpret. A passthrough network load balancer can preserve packet information and leave connection termination with the backend. On AWS, a TCP listener can pass encrypted traffic through so the target, rather than the Network Load Balancer, performs mutual TLS authentication.

This limits what a shared intermediary can accidentally rewrite, record, or replay. It also keeps domain decisions near the code that knows whether a checkout operation is idempotent.

Its risk is fragmentation. Certificate handling, request IDs, abuse controls, and security fixes can drift across services. An emergency policy may require several deployments instead of one controlled change.

## Pick the failure you are equipped to own

Position A is strongest when a capable platform team can test and operate shared policy better than each service can. Position B is strongest when protocol authority, client identity, or application semantics must remain with the backend, or when no team can safely own a programmable central gateway.

Your turn: reply with your team size, traffic type, and highest-stakes failure. Then choose the mistake you would rather contain: one central policy breaking many services, or many services implementing critical policy differently.

---

*Tomorrow, 09:00: the Week 1 recap and quiz across CAP, PACELC, consistent
hashing, Dynamo, and load balancing. The reverse-proxy weekend challenge
follows at 17:00.*
