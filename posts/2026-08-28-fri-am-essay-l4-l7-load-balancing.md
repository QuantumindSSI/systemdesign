# Week 1 · Fri 2026-08-28 · Long-form: L4 vs L7 Is a Trust-Boundary Decision, Not a Speed Test

> Calendar row: W1 Fri AM, 09:00. Format: contrarian take. Pillar: System
> Design Fundamentals. Pass: Foundations. This revision deliberately does
> not reuse Thursday's load-balancing algorithms, simulation, or measured
> results. Thursday asked how a balancer selects a backend. This essay asks
> where connections terminate and which component is trusted to interpret,
> change, log, retry, or reject application traffic.
>
> Sources re-checked 2026-08-28:
> - `github.com/donnemartin/system-design-primer`, "Layer 4 load balancing"
>   and "Layer 7 load balancing" sections, for the conventional definitions.
> - Google Cloud, "Choose a load balancer," for the documented distinction
>   between proxy and passthrough load balancing, direct server return,
>   connection termination, and client-IP preservation. Page last updated
>   2026-08-26 UTC.
> - AWS, "Listeners for your Network Load Balancers," for TCP passthrough
>   versus TLS termination on the same Layer 4 product family.
> - AWS, "What is an Application Load Balancer?" and "Target groups for your
>   Application Load Balancers," for content-based listener rules, front-end
>   TLS termination, HTTPS connections to targets, and gRPC-aware routing.
> - Envoy, "HTTP connection management," "HTTP routing," and "HTTP filters,"
>   for request decoding, access logs, request IDs, tracing, header handling,
>   route tables, retries, retry budgets, and filter-ordering risk.
> - RFC 9110, section 9.2.2, for HTTP idempotency and automatic-retry limits.
>
> Adversarial review record (2026-08-28):
> - No algorithm comparison or figure from Thursday appears below.
> - The essay does not equate L4 with passthrough. It explicitly covers L4
>   passthrough, L4 proxying, and TLS termination on a Network Load Balancer.
> - TLS termination is not described as necessarily creating a plaintext
>   backend hop; AWS documents HTTPS target groups for re-encryption.
> - Request retries are presented as a responsibility with idempotency and
>   retry-storm constraints, not as an automatic L7 benefit.
> - All scenarios are explicitly hypothetical. No invented engineer, quote,
>   incident, benchmark, or production scar is presented as fact.
> - Zero em dashes.

---

**Topic:** Layer 4 vs Layer 7 load balancing as a decision about connection ownership, trust, and failure authority

**Subtitle:** Instead of choosing between "fast" and "smart," you will learn to place TLS keys, client identity, retries, and protocol policy on the side of the boundary your team can safely operate.

Happy Friday. If you have ever sat in a design review while someone drew two boxes labeled "L4" and "L7," you probably know what came next. L4 was called fast and simple. L7 was called slower but smarter. Someone chose a side, the diagram moved on, and the hardest part of the decision disappeared under two layer numbers.

That summary is not useless. It is just too small for the job we ask it to do.

Yesterday, we cared about how a balancer chooses among backends. Today is a different question. Before any selection policy runs, who accepts the client's connection? Who holds the certificate? Who can see the HTTP method, path, headers, or status code? Who is allowed to rewrite them? If a request is retried, which component made that decision? When an investigator asks what the original client sent, which record can they trust?

Those are not performance trivia. They are ownership and trust decisions. "L4 or L7?" is useful only after it helps you answer them.

## The familiar answer is tidy, and incomplete

Let us give the standard explanation its strongest version first.

The System Design Primer says a Layer 4 balancer generally uses transport information such as source and destination IP addresses and ports, "but not the contents of the packet." Its Layer 7 balancer reads application-layer information such as headers, messages, and cookies, then makes a routing decision. That gives us the familiar picture: an L4 balancer directs sealed parcels by the address outside, while an L7 balancer opens the parcel and reads the delivery note.

From there, "L4 for speed, L7 for features" sounds reasonable. Looking at fewer fields usually means less work. Understanding HTTP creates options that opaque forwarding cannot provide, including path-based routing, redirects, authentication, and request-level policy.

The trouble begins when we turn those tendencies into architecture rules. An L4 product is not necessarily a passthrough device. A passthrough device is not the same thing as a TCP proxy. TLS can terminate on a product marketed as a Network Load Balancer. An L7 proxy can terminate the client TLS connection and still open an encrypted HTTPS connection to its backend. The label tells you roughly what information can influence a decision. It does not, by itself, tell you where every connection or encryption boundary sits.

The product documentation makes this concrete. [Google Cloud's load-balancer guide](https://cloud.google.com/load-balancing/docs/choosing-load-balancer) distinguishes proxy Network Load Balancers from passthrough Network Load Balancers. Both are network products, but the proxy terminates the incoming client connection and opens a new connection to a backend, while the passthrough form leaves connection termination to the backend and supports direct server return. Meanwhile, [AWS Network Load Balancer listeners](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html) can be configured as TCP, which passes encrypted traffic through, or TLS, which decrypts traffic at the load balancer and requires a server certificate there.

So the first contrarian point is simple: the layer number is not the decision. It is a clue. The decision is where traffic changes ownership.

## Draw the handoff before choosing the product

Imagine leaving a package at the front desk of an apartment building. One front desk checks the address and lets the courier continue to the resident. Another accepts the package, records it, opens it under an agreed policy, and sends a new internal delivery upstairs. Both can direct traffic. Only one becomes responsible for what happens at the handoff.

That handoff is what a useful load-balancer diagram should show. Draw the client on the left, the backend on the right, and the balancer between them. Then answer four separate questions:

| Decision | Options | What changes |
|---|---|---|
| Connection | Passthrough or proxy | Whether the backend or intermediary terminates the client connection |
| Encryption | TLS at the backend, at the intermediary, or at both | Where private keys live and where plaintext can exist |
| Protocol | Opaque bytes or application-aware messages | Whether the intermediary can act on methods, paths, headers, and status codes |
| Identity | Original packet identity or forwarded metadata | How the backend determines who actually connected |

These choices often travel together, but they do not have to. Google documents a network-layer proxy that terminates TCP without becoming an HTTP-aware application balancer. AWS documents TLS termination on a Network Load Balancer. AWS also documents HTTPS target groups behind an Application Load Balancer, which means traffic can be decrypted at the edge and encrypted again for the backend hop.

That is why a box labeled only `L4` or `L7` is not finished. Add marks where the client connection ends, where the backend connection begins, where TLS ends and restarts, and where application messages first become visible. Once those marks are on the page, the real review can begin.

## The certificate tells you where trust moved

Start with TLS because it turns an abstract layer choice into something your security and operations teams can point at.

If encrypted traffic passes through the balancer unchanged, the backend presents the certificate and proves its identity to the client. The backend also handles protocol negotiation and owns the private key. The intermediary can route using network and transport information, but it cannot inspect an encrypted HTTP path or sanitize an application header it cannot read.

If TLS terminates at the balancer, the client is establishing its protected session with that balancer. The certificate and private key now live there. This can make certificate renewal and cipher policy easier to centralize, but it also makes the balancer part of the security boundary. A configuration mistake, vulnerable parser, or unauthorized operator at that layer has a wider view than a component forwarding opaque traffic.

Now add the backend hop. Terminating TLS at the edge does not force you to send plaintext through the private network. AWS Application Load Balancer target groups support HTTPS, and the load balancer establishes a separate TLS connection to those targets. That creates two encrypted sessions with a deliberate trust boundary between them: client to balancer, then balancer to backend. The balancer can inspect and enforce application policy in the middle, but it must also be trusted with plaintext while processing the request.

This is a more useful conversation than "L4 is faster." Ask instead: where may plaintext exist, who may hold the certificate, and does the backend need the client's TLS session to reach it unchanged? Mutual TLS is a good forcing function. AWS's Network Load Balancer documentation says its TLS listeners do not support mutual TLS authentication and recommends a TCP listener when the target must perform mTLS itself. That is not a small feature checkbox. It determines which component authenticates the client.

When a requirement says "end-to-end encryption," do not accept the phrase until the diagram identifies the endpoints. Client to edge and edge to service can both be encrypted while still giving the edge access to the application message. Client directly to service through a passthrough balancer is a different trust model. The same green padlock can sit in front of both.

## Client identity can become a claim instead of a fact

The next handoff is less visible until rate limiting, abuse response, or audit work depends on it.

With passthrough load balancing, the backend can receive the original packet information. Google specifically recommends its passthrough Network Load Balancer when preserving client source IP addresses and packet information matters. With a proxy, the backend sees a new connection from the proxy tier unless the system carries the original identity separately. Google's guide says proxy load balancers do not preserve client IP addresses by default.

Application proxies commonly forward client information as trusted metadata. That is useful, but it changes the nature of the evidence. A source address observed from the network stack is one thing. A header saying "the original client was this address" is a claim made by an intermediary. The backend must know which proxies are trusted to make that claim, reject or overwrite client-supplied copies, and avoid treating an arbitrary inbound header as proof of identity.

Think of a visitor badge. If the security desk issues it, the office upstairs can rely on it because the office trusts the desk and knows visitors cannot print their own badges. If anyone can walk in wearing a handwritten badge, the same workflow becomes an impersonation bug. Forwarded identity works the same way: its safety comes from a controlled trust path, not from the header name.

This affects more than logging. IP-based allowlists, geographic controls, abuse limits, and forensic trails all depend on knowing whether the application sees the original transport identity or a proxy's assertion about it. If your design review never names that distinction, "we preserve client IP" is a hope, not a property.

## Reading HTTP means owning HTTP

The usual pitch for L7 is path-based routing. `/video` goes to one service, `/billing` to another. That is real, and [AWS's Application Load Balancer documentation](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html) lists path, host, method, header, query, and source-IP conditions among its routing capabilities.

But routing is the least interesting part of becoming application-aware.

Envoy's documentation describes the handoff precisely. Its HTTP connection manager translates raw bytes into HTTP-level events such as headers, body data, and trailers. Once it can do that, it can also generate request IDs, produce access logs and tracing data, manipulate headers, maintain route tables, apply filters, enforce timeouts, and retry requests. The proxy has not merely learned a smarter address. It has become a participant in the protocol.

That can be wonderful. One team can enforce authentication before traffic reaches any service. A request ID can follow a call from the edge into the application. Header sanitization can happen consistently. A malformed request can be rejected once instead of reaching several parsers with different behavior. A route can move between services without asking every client to change.

It can also concentrate risk. A bad route rule can misdirect every request matching it. A header rewrite can change application behavior. A filter ordering mistake can create a security gap. Envoy's own HTTP-filter documentation warns that changing routing inputs after route-dependent authorization has already run can make later filters observe a different route from the authorization filter. That is a concrete example of the price of central power: the proxy can make consistent decisions for the whole platform, including consistently wrong ones.

An L4 path leaves more of that authority with the backend. It can carry protocols the intermediary does not understand, and application teams keep control of parsing, authentication, and protocol evolution. The price moves rather than disappears. Each service may implement policy differently, observability is harder to standardize, and a fix that could have been one edge rule may need to ship across a fleet.

So "smart" is not a free adjective. Every feature at the L7 boundary is also an operational duty owned by the team running that boundary.

## Retries reveal who is allowed to change history

Consider a hypothetical checkout request. The backend accepts it, writes the order, and then the connection fails before the response reaches the proxy. An application-aware intermediary can see enough of the exchange to retry. That sounds resilient right until the same purchase happens twice.

HTTP has rules for this. [RFC 9110 section 9.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods) defines idempotent methods and limits when a client should automatically retry a non-idempotent request. Real systems can add idempotency keys and application-specific guarantees, but the proxy cannot invent those guarantees merely because it recognizes HTTP.

Envoy exposes retry conditions, timeouts, host-selection rules, and retry budgets. Its documentation explicitly recommends budgets or an active-retry circuit breaker to avoid retry storms. Again, visibility creates authority, and authority creates a new failure mode. An opaque forwarding layer cannot retry one HTTP request based on its status because it cannot identify that semantic unit. An L7 proxy can, which means someone must specify when it is safe, how much extra traffic is allowed, and where retry attempts are recorded.

This is the question hidden by "L7 has more features": who is allowed to decide that an operation should happen again?

If the answer is the edge, the edge needs method-aware policy, bounded retries, an idempotency story, and observability that distinguishes original requests from attempts. If the answer is the application, disable or narrowly scope intermediary retries and let the service use domain knowledge the proxy does not have. Both can be correct. Accidentally letting both retry is how a short backend wobble becomes multiplied load.

## Better visibility also creates sensitive records

There is one more ownership transfer to make explicit. An L4 system can observe connections, bytes, addresses, ports, resets, and timing. An L7 system can additionally observe application fields such as hosts, paths, methods, status codes, and selected headers. That usually makes incident investigation far easier.

It also means the proxy's logs may contain customer identifiers, search terms, tokens placed in URLs, or other sensitive material. The same access log that answers "which route returned errors?" may become a data-governance problem if retained too long or exposed too broadly. Visibility is not just an observability win. It is a data collection decision.

Before choosing L7 for better debugging, decide which fields may be logged, which must be redacted, who can query them, and how long they live. Otherwise the architecture solves one incident-response problem by creating a privacy problem no diagram mentioned.

## Use five questions instead of one slogan

At your next design review, set aside "L4 or L7?" for five minutes and answer these instead:

1. **Where must the client connection terminate?** If the backend must own the original connection or the protocol is not one your proxy understands, passthrough is a strong starting point. If you need a managed intermediary to absorb and proxy connections, draw the second backend connection explicitly.
2. **Where may TLS terminate, and where must it restart?** Name the components that hold private keys, authenticate clients, negotiate protocols, and can see plaintext. Treat front-end and backend encryption as separate choices.
3. **Which application decisions must be centralized?** Path routing, authentication, header policy, request IDs, timeouts, retries, and rate limits all argue for an application-aware boundary only when you are prepared to operate them there.
4. **How will the backend establish client identity?** Decide whether it receives original packet information or trusted metadata from a proxy, and document the trust chain that prevents clients from forging that metadata.
5. **What is the acceptable blast radius of a policy error?** A central L7 rule can protect every service at once and break every service at once. Distributed policy reduces that shared control point but invites drift.

Now try the questions against three concrete shapes.

For a public HTTP API that needs central certificate management, host and path routing, uniform authentication, request tracing, and a web application firewall, an L7 application proxy is doing work the platform genuinely needs. Re-encrypt to the backends if the trust model requires it, scope retries by application semantics, and treat proxy configuration as production code.

For a custom TCP protocol where the backend must authenticate the client's certificate directly, or where preserving original packet identity is a hard requirement, L4 passthrough is not the less sophisticated option. It is the architecture that refuses to insert an application authority where one does not belong.

For a large public system with several protocols, the answer may be layered: a network front door for broad transport coverage and stable addressing, then application-aware proxies only for traffic that needs application policy. The important part is not that both layer numbers appear. It is that each handoff has one reason to exist and one team that owns it.

Notice what did not appear in those decisions: a universal claim that one layer is faster. Performance still matters, but it should be measured against your product, traffic, and configuration after the trust model is correct. A microbenchmark cannot tell you who should hold your keys or whether a proxy is allowed to retry a purchase.

## The heuristic has limits too

"Choose the trust boundary" is better than "fast versus smart," but it is not a product selector by itself.

Managed load balancers bundle capabilities in ways that do not map neatly onto textbook layers. AWS can terminate TLS on a Network Load Balancer. Google offers both proxy and passthrough network load balancers. Application load balancers differ in protocol versions, authentication integrations, source-IP behavior, health checks, logging, regional scope, and backend encryption. Two products wearing the same layer label can produce different connection diagrams.

There is also no rule that centralization is always safer. A mature platform team may operate one hardened L7 boundary better than dozens of services could operate their own edge policy. A small team may create more risk by adopting a programmable proxy surface it does not know how to test. The right placement depends on ownership capacity as much as feature need.

That is the limit of today's argument: it cannot choose for you. It can stop you from choosing on the wrong axis.

## What to put on the whiteboard

The next time an architecture diagram shows a load balancer, add four marks before approving it: the client-connection endpoint, the backend-connection start, each TLS endpoint, and the source of client identity. Then write beside the balancer every application action it is authorized to take: route, authenticate, rewrite, log, rate-limit, retry, or reject.

If that list is empty, a simpler network path may be enough. If the list is long, you are not buying a smarter traffic distributor. You are creating a shared application control plane, and it deserves the same threat modeling, testing, rollout discipline, and ownership clarity as the services behind it.

That is the useful version of L4 versus L7. Not fast versus smart. Not old versus modern. It is a decision about where a connection becomes your responsibility, who is trusted to read it, and how much of the system that component is allowed to change when it acts.

---

*This afternoon, 17:00: the strongest cases for centralizing application
policy at the load balancer and for keeping traffic opaque until it reaches
the service. Pick the boundary you would trust with your own system. Tomorrow,
09:00: the Week 1 recap and quiz, followed by the reverse-proxy weekend
challenge at 17:00.*
