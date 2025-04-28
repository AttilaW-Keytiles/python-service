package testsuiteconfig

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
)

const (
	TESTSUITE_JAR_TO_USE = "jbehave-bdd-test-suite-1.1.0.jar"
	STORY_TIMEOUT_SECS   = "120"
)

// This simple test case basically bootstraps and executes all jBehave integration tests. And fails if it did not return clean.
// This way if we execute 'go clean -testcache'
//
// CAUTION! These tests are - since they are not based on test code - is more likely to use cached results!!!
// It is a good idea to execute 'go clean -testcache' before this.
func Test_IntegrationTestScenarios(t *testing.T) {

	wd, _ := os.Getwd()
	testFolder := strings.ReplaceAll(wd, "\\", "/") + "/"
	jarPath := testFolder + TESTSUITE_JAR_TO_USE

	// check if we have the .jar
	_, err := os.Stat(jarPath)
	if err != nil && errors.Is(err, os.ErrNotExist) {
		assert.FailNowf(t, "Oops it looks the testsuite .jar '%s' does not exist! You have to download it!\nreleases: https://nexus.keytiles.com/nexus/content/repositories/public-releases/com/keytiles/tool/jbehave-bdd-test-suite/ or\nsnapshots: https://nexus.keytiles.com/nexus/content/repositories/public-snapshots/com/keytiles/tool/jbehave-bdd-test-suite/", jarPath)
	}

	// looks good, lets execute the tests!
	command := "java"
	args := []string{
		//"-version",
		"--add-opens",
		"java.base/java.lang=ALL-UNNAMED",
		"-DuseStoryTimeout=" + STORY_TIMEOUT_SECS,
		"-jar",
		jarPath,
		"-testsSetupFolder",
		testFolder,
	}
	cmd := exec.Command(command, args...)
	// cmd.Env = append(os.Environ(),
	// 	"FOO=duplicate_value", // ignored
	// 	"FOO=actual_value",    // this value is used
	// )

	output, err := cmd.CombinedOutput()
	// we print the output anyways
	fmt.Printf("'%s' command output:\n%s\n", command, string(output))
	// and fail the test in case exit code was not 0 (that returns an error)
	assert.NoErrorf(t, err, fmt.Sprintf("It looks test run returned error. Tests did not went well for sure for some reason... error: %s", err))

}
