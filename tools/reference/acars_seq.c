/*
 * acars_seq: parse ACARS blocks in order with libacars' reassembly, as dumphfdl
 * configures it (HFDL bearer). Reference for conformance/parse/acars.json.
 *
 * stdin, one block per line:  <time_s> <u|d> <hex of the octets after SOH>
 * stdout, one JSON object per line (libacars' JSON of the block).
 *
 * Build: gcc -O2 -I/usr/local/include/libacars-2 -o acars_seq acars_seq.c -lacars-2
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <libacars/libacars.h>
#include <libacars/acars.h>
#include <libacars/reassembly.h>
#include <libacars/vstring.h>

int main(void) {
	la_config_set_int("acars_bearer", LA_ACARS_BEARER_HFDL);
	la_reasm_ctx *ctx = la_reasm_ctx_new();
	char line[65536];
	while(fgets(line, sizeof(line), stdin) != NULL) {
		double t = 0;
		char dir = 0;
		static char hex[65536];
		if(sscanf(line, "%lf %c %65535s", &t, &dir, hex) != 3) {
			continue;
		}
		size_t n = strlen(hex) / 2;
		unsigned char *buf = malloc(n ? n : 1);
		for(size_t i = 0; i < n; i++) {
			unsigned v;
			sscanf(hex + 2 * i, "%2x", &v);
			buf[i] = (unsigned char)v;
		}
		struct timeval tv = { .tv_sec = (time_t)t, .tv_usec = (suseconds_t)((t - (double)(time_t)t) * 1e6) };
		la_proto_node *node = la_acars_parse_and_reassemble(buf, (int)n,
				dir == 'u' ? LA_MSG_DIR_GND2AIR : LA_MSG_DIR_AIR2GND, ctx, tv);
		la_vstring *vs = la_proto_tree_format_json(NULL, node);
		printf("%s\n", vs->str);
		la_vstring_destroy(vs, true);
		la_proto_tree_destroy(node);
		free(buf);
	}
	la_reasm_ctx_destroy(ctx);
	return 0;
}
