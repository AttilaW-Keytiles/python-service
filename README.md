
# What's this?

A simple service implemented in Python to handle Customers and Bank accounts CRUD and other operations.

# How to use?

Service comes with an HTTP API - as a start see [banking-api.yaml](api/banking-api-v1.yaml) OpenApi contract for details! (Preferably use Swagger UI on it!)

To fire up the Service locally
 * First of all make sure you have Python installed. Just quickly
    * Open a Terminal (Linux)
    * execute: `$ python -version`
    * Did it work? If not then you dont have Python properly installed. Install it!
 * Python-native way: just use `run-service.sh`.  
   This will build everything needed to run the Service locally.
 * Alternatively, you can also fire up as a Docker container (**TODO** Later! Not implemented yet)

# Versioning and changes

We follow [Semantic versioning](https://semver.org/) with the code. For detailed changes see [CHANGELOG](CHANGELOG.md) for more details.

**PLEASE NOTE!** Version of the code is not equal to version of public interfaces! Public interfaces (e.g. HTTP API) have their own versions!



# How to contribute?

Later... :-P but useful section

# For contributors / developers

## Getting started

You will need a nice IDE - consider using VSCode maybe.

### Virtual Env

Code is using Virtual Environment - not committed to repo as it could be big! But you will need it.

When you cloned the repo fresh execute the following command once to get the env created and all dependencies added to it:
 1. Open a Terminal (Linux) and go to the project folder
 1. Execute the init script: `$ dev-init.sh`

Now you have the Python environment with all used dependencies - **including Test dependencies!**

## Run the service locally

When you want to run the code you need to activate this environment:
 1. Open a Terminal (Linux) and go to the project folder
 1. execute: `$ source .venv/Scripts/activate` OR alternatively you can just use simply `run-service.sh`

## Sending in HTTP requests

This brings up everything, by default HTTP server is started on localhost:8080.

Just open the contract - [banking-api-v1.yaml](api/banking-api-v1.yaml) with Swagger UI. And you will see all endpoints.

**IMPORTANT!** You may notice all endpoints **require Authentication**.
It is easy, we have one 'root' user configured - see [initial_data_users.sql](db_schemas/sqlite/initial_data_users.sql)! You see the username and password there! This is what you can use. Just put it to Basic Auth!

You also find an exported [Postman](https://www.postman.com/downloads/) collection here: [Banking API.postman_collection.json](api/Banking%20API.postman_collection.json). Use it if you wish!

## Configuring the service

You find the config of the service here: [local_workfolder/conf/config.yaml](local_workfolder/conf/config.yaml). Feel free to take a look!

And you can also configure the logging which is here [local_workfolder/conf/log-config.yaml](local_workfolder/conf/log-config.yaml).

By default logging is configured the way it is logging to console, plain text.  
But it also logs into files in "local_workfolder/logs" into two files - one plain test "service.log" and another JSON JSON file and format into "service.log.json" files.

We are using "structured logging" - but you will read about it later too.

## Debug the code

To debug the code:
 1. In VSCode just open `main.py`
 1. You need to pass some arguments on command line so you add launch config. The main point is you have a `.vscode` folder in you project and `launch.json` inside in which
    you should have a `"args"` entry to make sure service starts using the prepared config and log-config, like this:
    ```yaml
    "configurations": [

        {
            "name": "Python Debugger: Current File with Arguments",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "args": ["--cfg", "local_workfolder/conf/config.yaml", "--logCfg", "local_workfolder/conf/log-config.yaml"]
        }
    ]    
    ```
  1. Now you can hit the "Run & Debug" icon on the left and simply start the launch config. It should bootstrap everything nicely

## Run tests

Tests are located in the `/test` folder on the project root.

They follow the same package structure az code does under `/src` folder.

Tests are written in **PyTest**.

To run them from command line
 1. Open a Terminal (Linux)
 1. execute `$ python -m pytest`  
    (this will help on problem described here: https://stackoverflow.com/questions/20985157/py-test-no-module-named)

To run individual tests from VSCode right-click, you need to configure your VSCode just once.  
I followed this: https://pytest-with-eric.com/introduction/how-to-run-pytest-in-vscode/


## Folder structure

Quickly write down which folder is what? However many of them is obvious...

 * **api** - Contains the OpenApi contracts. Also the .sh file to generate models out of (modified) contracts. And Postman request collection. Can be handy...
 * **db_schamas** - used to create SQL schemas
 * **local_workfolder** - just see its [README](local_workfolder/README.md)
 * **src** - the source code of the Service - organized into packages
 * **test** - contains PyTest tests - following same package structure as code (hopefully)

## Package structure

Within the [src](src/) folder we structure the Service source code into packages.

We followed "Clean architecture" principles basically so that might give a good guess if you know this immediatelly.
If you don't know what it is, watch my presentation on YouTube! :-P just visit https://youtu.be/ENNoHz4i3Rk

But here they are - in a dependency order

 * **model** - As name suggests contains model classes. Stuff here are in the very center of the Application core. Everyone is depending on them. And they might cross-depend on each other as well.
 * **util** - Just some useful stuff. To DRY.
 * **observability** - Utility. Would externalize into a lib actually. It brings useful abstraction to implement some good standards in terms of Logging and Monitoring (metrics)
 * **context** - Helps to establish a business transaction top-down when someone calls the Service any public endpoint. TransactionId helps to correlate call-chain. And connected with Logging is very helpful
 * **controller** - Here we have the "use cases" so to speak. The main business logic is implemented here - "what can we do with what". These are operating on top of Models and orchestrating them. They also phrase their "requirements"
                    by defining interfaces (Ports). Which we implement somewhere.
 * **persistence** - Controllers are defiining so called "Ports" (interfaces) - persistence related. Defining their "requirement". In this folder we find the implementation of those (Adpaters) for concrete DB servers. For now only Sqlite.
 * **api** - For now only the HTTP api. But could be gRPC or whatever else added too. These handlers are simply "translating" the incoming HTTP requests to Controllers. And they are relatively dump. But they know how to convert results
             returned and errors raised by Controllers back to HTTP to fulfill our Contract.

## Design decisions / considerations

### General remarks

 1. First of all a quick note: Python is not really my "primary language" to implement services or complex problems... :-)
    So excuse my (likely) language related newbie mistakes - just be gentle with me... Thanks!

 1. Intentionally wrote / designed some things the way it can (should) trigger some cool discussions... 
    Your reactions will also help me to get a feeling about "mindset" readiness to develop SaaS / SOA stuff meant to be a Product... So yes, I'm provoking a bit ;-)

 1. Since you wrote build stuff "as if it were going into production"
    * I have added configurability
    * Metrics (Monitoring) and Logging  
      Logging waorks the way it is configurable, hierarchical, structured logging - with scraping-ready (if you configure) JSON format
    * Minimalistic service-global meta data (taken from ENV, prepared for Dockerization) - goes into both Metrics and Logging "global labels" (collection ready) 
    * Some tracing possibilities - minimalistic but most useful (TraceID / TransactionID only for now)

 1. For maintainability:
    * Used "Clean architecture" principles (not overdone, simplified!) for code structuring (package design)
    * "Ports & Adapters" pattern - e.g. this way can start with SQLite persistence but has the possibility to switch later relatively cheap
    * Using interfaces opens a way to use "Dependency injection" and more configurability - so let's do it!
      (No framework or inversion of control is involved - we just "wire" manually for now)
    * Try design things the way out of the box we do not lock ourselves "too much" to any concrete libraries or frameworks.
    * Implement DRY (Do not Repeat Yourself) - and eliminate boilerplate as much as possible - out of the business logic

 1. What I DID NOT bother with / skipped for now
    * Sophicticated error handling - like "retry policy", translation friendly errors etc. Did not worth it with the task.
    * Speed optimization. I skipped Python "async" topic for now.
    * Left out a few layers which are normally there in a product. (See API remark of error handling for example)
    * Extracting certain things into libs (e.g. 'observability' package) making them slim, inter-service reusable shared code.
      Of course such step also would involve prior discussions and agreement in certain standards. Now this is not in the focus.
      So everything is implemented in-place within this only service.
    * Employee passwords stored raw in DB - WHHHAAAAATTTT? :-) OK for now.
    * Data consistency is not full. You can not create an Account for a non-exissting Customer BUT the other way around works. Meaning that e.g. you can create a Customer, then an Account
      and then delete the Customer. It will just simply work.  
      The Customer would vanish however the Account would still refer to his prior id. I think fine for now...

 
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

#### prometheus-client

The official one to support Metrics. However this has a major drawback... Summary does not support quantiles... :-( It's a real shame as I do not really like Histograms. Why? I can tell you in spoken words :-P

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
 * There is no DELETE on accounts. Not a coincidence...

### Handy tools

Here are a few handy tools for your work:

 * SQLite Browser - https://sqlitebrowser.org/dl/  
   It's handy if you use the so far implemented Sqlite DB backend. The DB file you find where you configured to be :-) See [config.yaml](local_workfolder/conf/config.yaml) - `persistence/sqlite/db_file` entry!


 ## TODO

Design / Functionality related:
 * DAO layer is using the generated models out of API for now. Mmmmmmm not good... DAO layer should have its own. See placeholder: [db TODO](src/model/db/TODO.md)
 * Customers can not initiate Transfers from their own accounts. Although 'customer_id' link is there in user table, not used at the moment.
 * When Transfer is created there is no DB transaction boundary! And this is really not a good idea for production... All DB operations should go "all or none" fashion!

Simple tasks:
 * logging: Uvicorn log integration is not good - comes with empty labels and this way would not be correctly collected.
   Should take a closer look into python.logging package to check if we can capture the LoggerFactory / Logger somehow. And if yes refactor our logging package to step in there too for providing global labels there too.
 * Python best practice: go through code and change all var/param/method names from camelCase to snake_case. camelCase is too much in my hand.. :-)

## Pitch - some Topics to talk about

 * Just go through the API part bullets quickly. Many interesting topics are there...

 * Drawback of introducing MessageResponse into the API contract in case of 401, 403.
   Reminder: you must code, can not simply leverage framework-provided Auth no brainer

 * Consequence of following "Clean architecture" - if we take principles by the book.  
   Example: take a look on Controller <-> Persistence cooperation! Where we used "Ports & Adapters" pattern to
   achieve inwards dependency. How would my DAO layer look like after having 10+ Controllers?
 
 * Consequence of "Ports & Adapters": interesting situation we see with IAccountOperations_DAO... Now the implementor find himself in a situation however he is Accounts related DAO
   now still needs to deal with Transaction related stuff... see method [SqliteAccountDAO](src/persistence/sqlite/sqlite_account_dao.py).get_account_transfers() method! We are
   full of Transfer objects... Structure clearly indicates we got into trouble - left it there, intentionally! As life is life.  
   Tip: we have TODOs all over places - Jira ticket ID mentioning would be much much better to correlate all ;-)

 * Errors - take a look into [errors.py](src/model/error/).  
   Yes, they are "models".

 * The /src/context package - ExecutionContext

 * Tests...  
   One not bad unit test which is testing pretty good an Adapter is: [test\persistence\sqlite\sqlite_customer_crud_dao_test.py](test\persistence\sqlite\sqlite_customer_crud_dao_test.py).  
   It is testing out the Adapter object - due to fact it is Unit test it fails fast, price is low.  
   But! Only for the execution... What about maintenance? Overlap with Integration level tests. Do we need this so extensive??? Pros / Cons of this??? What to test where?
