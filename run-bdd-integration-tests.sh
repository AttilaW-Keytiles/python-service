#!/bin/bash

#
# You can use this shell script to execute the BDD integration tests
# This way of running the tests working with long story timeout - so you have enough time to debug into the code!
#
# Please note: there is also a Python test file which basically does the same - execute all tests. But that guy does not work with long timeouts
#

testSetupFolder=bdd-integration-test/testsuite-config
testSuiteJar=jbehave-bdd-test-suite-1.2.0.jar
# to have enough time to debug if you want
storyTimeoutSecs=3600

jarFullPath="$testSetupFolder/$testSuiteJar"

echo "jar path: $jarFullPath"

if [ ! -e $jarFullPath ]
then
    echo "FAILURE! The test suite jar file does not exist: $jarFullPath"
    echo "Download it from Nexus and make sure the 'testSuiteJar' variable value is correct!"
    echo "Nexus links:"
    echo "  - releases: https://nexus.keytiles.com/nexus/content/repositories/public-releases/com/keytiles/tool/jbehave-bdd-test-suite/"
    echo "  - snapshots: https://nexus.keytiles.com/nexus/content/repositories/public-snapshots/com/keytiles/tool/jbehave-bdd-test-suite/"
fi

cmd="java --add-opens java.base/java.lang=ALL-UNNAMED -DuseStoryTimeout=$storyTimeoutSecs -jar $jarFullPath -testsSetupFolder $testSetupFolder"
echo "executing now the test suite with java..."

$cmd
