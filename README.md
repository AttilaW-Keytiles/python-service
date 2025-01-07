
# What's this?

A simple service implemented in Python to handle Customers and Bank accounts CRUD and other operations.

# How to use?

Service comes with an HTTP API - as a start see [banking-api.yaml](api/banking-api.yaml) OpenApi contract for details! (Preferably use Swagger UI on it!)

To fire up the Service locally
 * Python-native way: just use `run-service.sh`.
 * Alternatively you can also fire up as a Docker container (TODO Later! Not implemented yet)

# Versioning and changes

We follow [Semantic versioning](https://semver.org/) with the code. For detailed changes see [CHANGELOG](CHANGELOG.md) for more details.

**PLEASE NOTE!** Version of the code is not equal to version of public interfaces! Public interfaces (e.g. HTTP API) has it's own versions!

# How to contribute?

Later... :-P but useful section

# For contributors

## Getting started

First of all make sure you have Python installed. Just quickly
 1. Open a Terminal (Linux)
 1. execute: `$ python -version`

Did it work? Good! Not? Then install Python!

You also need a nice IDE - consider using VSCode maybe.

### Virtual Env

Code is using Virtual Environment - not committed to repo as it could be big! But you will need it.

When you cloned the repo fresh execute the following command once to get the env created and all dependencies added to it:
 1. Open a Terminal (Linux) and go to the project folder
 1. Execute the init script: `$ dev-init.sh`

Now you have the Python environment with all used dependencies.

When you want to run the code you need to activate this environment:
 1. Open a Terminal (Linux) and go to the project folder
 1. execute: `$ source .venv/Scripts/activate` OR alternatively you can just use `run-service.sh`


## Design decisions / considerations

### General remarks

 1. First of all a quick note: Python is not really my "primary language" to implement services or more complex problems... :-)
    So excuse my (likely) language related newbie mistakes - just be gentle with me... Thanks!

 1. Intentionally wrote / designed some things the way it can (should) trigger some cool discussions... 
    Your reactions will also help me to get a feeling about "mindset" readiness to develop SaaS / SOA stuff meant to be a Product... So yes, I'm provoking a bit ;-)

 1. Since you wrote build stuff "as if it were going into production"
    * I have added configurability
    * Metrics (Monitoring) and Logging  
      Logging waorks the way it is configurable, hierarchical, structured logging - with scraping-ready (if you configure) JSON format
    * Minimalistic service-global meta data (taken from ENV, prepared for Dockerization) - goes into both Metrics and Logging "global labels" (collection ready) 
    * Some tracing possibilities - minimalistic but most useful (CorrelationID / TransactionID only for now)

 1. For maintainability:
    * Used "Clean architecture" principles (not overdone, simplified!) for code structuring (package design)
    * "Ports & Adapters" pattern - e.g. this way can start with SQLite persistence but has the possibility to switch later relatively cheap
    * Using interfaces opens a way to use "Dependancy injection" and more configurability - so let's do it!
    * Try design things the way out of the box we do not lock ourselves "too much" to any concrete libraries or frameworks.

 1. What I DID NOT bother with / skipped for now
    * Sophicticated internal error handling - like "retry policy". Did not worth it with the task.
    * Speed optimization. I skipped Python "async" topic for now.
    * Left out a few layers which are normally there in a product. (See API remark of error handling for example)
    * Extracting certain things into libs (e.g. 'observability' package) making them slim, inter-service reusable shared code.
      Of course such step also would involve prior discussions and agreement in certain standards. Now this is not in the focus.
      So everything is implemented in-place within this only service.

 
### 3rd party Libraries

Although I never really used Python to build complex things like Services (more just to build some offline tooling fast) I know exactly what I'm looking for when doing such task. From this
perspective I am "language agnostic" and much more design & best practices focused.

Considering this I made the following choices (debatable of course by a Python ninja...)

#### FastAPI

This library is in-theory light-weight but suitable for Production use. Syntax to declare and map HTTP handlers looks good and simple enough for both - as a atart and later more advanced stuff.

Pros:
 * We need a HTTP server - this brings it
 * We need transparent and evolvable Authentication/Authorization - checkmark
 * I wanted to use "dependency injection" - this stuff brings it out of the box

Cons:
 * Startup of the app... Instead of just using `python main.py` to fire up service it looks the by default recommended way is: `fastapi dev main.py` ...  
   I have the feeling we would quickly get into trouble if we would like to introduce another public API other than HTTP: gRPC for example. Or just replace FastAPI so googling around
   I found some way to get rid of it.

#### Structlog

I wanted to have structured logging. Using https://github.com/hynek/structlog adds a dev-friendly DSL to logging to handle this. (note: my CloudSolutions team also selected this in Agile Robots back then for 
this purpose after evaluating libraries and options)

#### json-log-formatter

If we want PROD ready (scrape ready) logs we need to format them into "1 line - 1 log event" and for this the JSON format fits well. So we needed a formatter.

### API

 * I follow "contract first" approach (which I prefer - can be discussed spoken words why). So we have generated models from the contract. But we do NOT have generated Server... again, can be discussed why.
 * Because of the above I am NOT interested in FastAPI's feature which can generate/display SwaggerUI OpenApi contract at all. Therefore skipping all related routing/method annotations everywhere.
 * API versioning is considered.
 * Did not leave endpoints fully unprotected but for now just quickly added the most basic Basic auth. So no GWT or other magic as a start.
 * Returned error responses are built the way they can be both machine and human readable. BUT!  
   To do not over do this for now skipped using more "inheritance" in OpenApi contract and not extending CommonErrorCodes with API specific extra values... as well as translation support.
 * Used a mixture of REST and RPC. For demo reasons. We can talk about it why / where.  
   Immediately added race condition detection to REST endpoints - using resource versioning. ("optimistic locking" pattern)
 * REST - POST requests: ID assignment... Should it fully happen on server side? Or also allow on Client side? Let's talk about pros/cons and why?
 * REST - DELETE operations: having 404 response or not having it is a design question. Teams who favor full idempotency typically never return 404 on these requests. While Teams who favor full transparency
   and control do. I have chosen transparncy here.
 * The API is relatively extensive but did not implement everything - too much time investment for a code challenge maybe? :-)

 ## TODO

 * logging: Uvicorn log integration is not good - comes with empty labels and this way would not be correctly collected.
   Should take a closer look into python.logging package to check if we can capture the LoggerFactory / Logger somehow. And if yes refactor our logging package to step in there too for providing global labels there too.
 * Python best practice: go through code and change all var/param/method names from camelCase to snake_case. camelCase is too much in my hand.. :-)

## Topics to talk about

 * Drawback of introducing MessageResponse into the API contract in case of 401, 403.
   Reminder: you must code, can not simply leverage framework-provided Auth no brainer