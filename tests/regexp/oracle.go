// The expected matches of util/regexp's tests, from Go's regexp, whose syntax
// and leftmost-first semantics are RE2's (tests/python/test_regexp.py,
// docs/regexp.md section 5).
//
// Each line of standard input is a case, "PATTERN SUBJECT" in hexadecimal (two
// digits a byte, - for none); each line of standard output is the case
// followed by its expected matches, in tests/regexp/corpus.quest's format:
// "PATTERN SUBJECT FULL PARTIAL", where FULL is the match of \A(?:PATTERN)\z
// and PARTIAL of PATTERN. A pattern Go does not compile gives "PATTERN SUBJECT
// error". Go matches UTF-8, so its answers are this library's only for ASCII
// patterns and subjects, which are all the test gives it.
//
// With -all, each output line is instead "PATTERN SUBJECT ALL SPLIT REPLACE":
// ALL the spans of every match (FindAllStringIndex), start-end, separated by
// ";", or - for none; SPLIT the pieces of Split(subject, -1) in hexadecimal,
// separated by ";", _ for an empty piece, or - for none; and REPLACE
// ReplaceAllString(subject, "<$0|$1>") in hexadecimal, - for an empty one.
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

func hexed(s string) string {
	if s == "" {
		return "-"
	}
	return hex.EncodeToString([]byte(s))
}

func spans(all [][]int) string {
	if len(all) == 0 {
		return "-"
	}
	parts := make([]string, len(all))
	for i, m := range all {
		parts[i] = fmt.Sprintf("%d-%d", m[0], m[1])
	}
	return strings.Join(parts, ";")
}

func pieces(ps []string) string {
	if len(ps) == 0 {
		return "-"
	}
	parts := make([]string, len(ps))
	for i, p := range ps {
		if p == "" {
			parts[i] = "_"
		} else {
			parts[i] = hex.EncodeToString([]byte(p))
		}
	}
	return strings.Join(parts, ";")
}

func main() {
	all := len(os.Args) > 1 && os.Args[1] == "-all"
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
		if all {
			fmt.Fprintf(out, "%s %s %s %s %s\n", fields[0], fields[1], spans(re.FindAllStringIndex(subject, -1)),
				pieces(re.Split(subject, -1)), hexed(re.ReplaceAllString(subject, "<$0|$1>")))
			continue
		}
		fmt.Fprintf(out, "%s %s %s %s\n", fields[0], fields[1],
			written(full.FindStringSubmatchIndex(subject)), written(re.FindStringSubmatchIndex(subject)))
	}
}
