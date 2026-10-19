// Operation "fund value at the second custodian", second implementation. Same contract as the Python one:
// fund, statement, pause -> JSON {fund, value_usd, rows, impl}. As a standalone program: arguments; as an expert: JSON on stdin.
package main

import (
	"bufio"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"os"
	"strconv"
	"strings"
	"time"
)

func num(v string) float64 { f, _ := strconv.ParseFloat(strings.Replace(v, ",", ".", 1), 64); return f }

func main() {
	var p struct {
		Fund, Statement string
		Pause           float64
	}
	if len(os.Args) > 2 {
		p.Fund, p.Statement = os.Args[1], os.Args[2]
		if len(os.Args) > 3 {
			p.Pause, _ = strconv.ParseFloat(os.Args[3], 64)
		}
	} else if json.NewDecoder(os.Stdin).Decode(&p) != nil {
		fmt.Fprintln(os.Stderr, "parameters are not readable")
		os.Exit(1)
	}
	f, err := os.Open(p.Statement)
	if err != nil {
		fmt.Fprintln(os.Stderr, "statement is not readable")
		os.Exit(1)
	}
	in := bufio.NewReader(f)
	if b, _ := in.Peek(3); len(b) == 3 && b[0] == 0xEF {
		in.Discard(3)
	}
	r := csv.NewReader(in)
	r.Comma = ';'
	r.Read()
	total, rows := 0.0, 0
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err == nil && strings.TrimSpace(row[0]) == p.Fund {
			total += num(row[3]) * num(row[4]) * num(row[6])
			rows++
		}
	}
	time.Sleep(time.Duration(p.Pause * float64(time.Second)))
	json.NewEncoder(os.Stdout).Encode(map[string]interface{}{"fund": p.Fund, "value_usd": math.Round(total*100) / 100, "rows": rows, "impl": "go-v2"})
}
