// The expected matches of util/regexp's tests, from Go's regexp, whose syntax
// and leftmost-first semantics are RE2's (tests/python/test_regexp.py,
// docs/regexp-plan.md section 5).
//
// Each line of standard input is a case, "PATTERN SUBJECT" in hexadecimal (two
// digits a byte, - for none); each line of standard output is the case
// followed by its expected matches, in tests/regexp/corpus.quest's format:
// "PATTERN SUBJECT FULL PARTIAL", where FULL is the match of \A(?:PATTERN)\z
// and PARTIAL of PATTERN. A pattern Go does not compile gives "PATTERN SUBJECT
// error". Go matches UTF-8, so its answers are this library's only for ASCII
// patterns and subjects, which are all the test gives it.
package main

import (
	"bufio"
	"encoding/hex"
	"fmt"
	"os"
	"regexp"
	"strings"
)

func unhex(h string) string {
	if h == "-" {
		return ""
	}
	b, err := hex.DecodeString(h)
	if err != nil {
		fmt.Fprintln(os.Stderr, "oracle: bad hex:", h)
		os.Exit(2)
	}
	return string(b)
}

func written(m []int) string {
	if m == nil {
		return "-"
	}
	parts := make([]string, len(m)/2)
	for i := range parts {
		if m[2*i] < 0 {
			parts[i] = "-"
		} else {
			parts[i] = fmt.Sprintf("%d-%d", m[2*i], m[2*i+1])
		}
	}
	return strings.Join(parts, ",")
}

func main() {
	in := bufio.NewScanner(os.Stdin)
	in.Buffer(make([]byte, 1<<20), 1<<24)
	out := bufio.NewWriter(os.Stdout)
	defer out.Flush()
	for in.Scan() {
		fields := strings.Fields(in.Text())
		if len(fields) != 2 {
			continue
		}
		pattern, subject := unhex(fields[0]), unhex(fields[1])
		re, err := regexp.Compile(pattern)
		full, errFull := regexp.Compile(`\A(?:` + pattern + `)\z`)
		if err != nil || errFull != nil {
			fmt.Fprintf(out, "%s %s error\n", fields[0], fields[1])
			continue
		}
		fmt.Fprintf(out, "%s %s %s %s\n", fields[0], fields[1],
			written(full.FindStringSubmatchIndex(subject)), written(re.FindStringSubmatchIndex(subject)))
	}
}
