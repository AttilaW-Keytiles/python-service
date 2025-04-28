
!-- these "Before" steps are executed before all scenarios
Lifecycle:
Before:

Scenario: 1  GetCustomer test

Given the Python application controlled by bean pythonServiceController with the following environment variables is running: fsfile://${setupFolder}/app-startup-envvars.json

Given 15 seconds passed

When the following HTTP request is sent:
    | method | url                                           | headers                                          |
    | GET    | http://localhost:8080/api/v1/customers/rest/2 | Authorization:Basic cm9vdDpBQnJha2FkYWJyYTEyMzQ= |
Then the following HTTP response is returned and order does not matter and body contains:
  | status | body                                                  | contentType      |
  | 200    | fsfile://${filesFolder}/customersTests/customer2.json | application/json |
