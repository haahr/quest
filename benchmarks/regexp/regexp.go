// regexp.quest's workloads with Go's regexp, for comparison
// (benchmarks/regexp/README.md): the same arguments, the same number printed.
package main

import (
	"fmt"
	"os"
	"regexp"
	"strconv"
	"strings"
)

func main() {
	workload, path := os.Args[1], os.Args[2]
	repeat, _ := strconv.Atoi(os.Args[3])
	data, err := os.ReadFile(path)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	text := string(data)
	lines := strings.Split(strings.TrimSuffix(text, "\n"), "\n")

	containing := func(r *regexp.Regexp) int {
		n := 0
		for _, line := range lines {
			if r.MatchString(line) {
				n++
			}
		}
		return n
	}
	summed := func(r *regexp.Regexp, f func(text string, m []int) int) int {
		n := 0
		for _, line := range lines {
			if m := r.FindStringSubmatchIndex(line); m != nil {
				n += f(line, m)
			}
		}
		return n
	}

	once := func() int {
		switch workload {
		case "walk":
			total := 0
			for _, line := range lines {
				total += len(line)
			}
			return total
		case "literal":
			return containing(regexp.MustCompile(`ERROR`))
		case "caseless":
			return containing(regexp.MustCompile(`(?i)error`))
		case "alternation":
			return containing(regexp.MustCompile(`\b(?:timeout|refused|reset|unreachable)\b`))
		case "prefix":
			return summed(regexp.MustCompile(`user=(\w+)`), func(_ string, m []int) int { return m[3] - m[2] })
		case "date":
			return summed(regexp.MustCompile(`(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)`),
				func(s string, m []int) int { h, _ := strconv.Atoi(s[m[8]:m[9]]); return h })
		case "anchored":
			return summed(regexp.MustCompile(`^([A-Z]+) `), func(s string, m []int) int {
				if s[m[2]:m[3]] == "WARN" {
					return 1
				}
				return 0
			})
		case "tokens":
			return len(regexp.MustCompile(`[A-Za-z_]\w*|\d+|"(?:[^"\\]|\\.)*"|\S`).FindAllStringIndex(text, -1))
		case "replace":
			return len(regexp.MustCompile(`\s+`).ReplaceAllString(text, " "))
		}
		fmt.Fprintln(os.Stderr, "regexp.go: no workload", workload)
		os.Exit(2)
		return 0
	}

	result := 0
	for i := 0; i < repeat; i++ {
		result = once()
	}
	fmt.Println(result)
}
