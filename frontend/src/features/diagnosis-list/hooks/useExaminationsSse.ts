import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { apiFetchStream } from "../../../lib/auth";

const RECONNECT_MS = 4000;

async function consumeExaminationsSse(
	queryClient: ReturnType<typeof useQueryClient>,
	signal: AbortSignal,
): Promise<void> {
	const response = await apiFetchStream("/api/examinations/events", { signal });
	if (!response.ok || signal.aborted) {
		return;
	}
	const reader = response.body?.getReader();
	if (!reader) {
		return;
	}
	const decoder = new TextDecoder();
	let buffer = "";
	while (!signal.aborted) {
		const { done, value } = await reader.read();
		if (done) {
			break;
		}
		buffer += decoder.decode(value, { stream: true });
		for (;;) {
			const sep = buffer.indexOf("\n\n");
			if (sep === -1) {
				break;
			}
			const block = buffer.slice(0, sep);
			buffer = buffer.slice(sep + 2);
			for (const line of block.split(/\n/)) {
				if (!line.startsWith("data: ")) {
					continue;
				}
				try {
					const data = JSON.parse(line.slice(6)) as { type?: string };
					if (data.type === "examinations_changed") {
						void queryClient.invalidateQueries({ queryKey: ["examinations"] });
					}
				} catch {
					/* malformed line */
				}
			}
		}
		if (buffer.length > 512_000) {
			buffer = buffer.slice(-128_000);
		}
	}
}

/**
 * MFER 取り込みなどの Server-Sent Events で診察一覧クエリを無効化する。
 */
export const useExaminationsSse = () => {
	const queryClient = useQueryClient();
	const queryClientRef = useRef(queryClient);
	queryClientRef.current = queryClient;

	useEffect(() => {
		const controller = new AbortController();
		let cancelled = false;

		const loop = async () => {
			while (!cancelled) {
				try {
					await consumeExaminationsSse(
						queryClientRef.current,
						controller.signal,
					);
				} catch {
					/* 切断・ネットワークエラー */
				}
				if (cancelled || controller.signal.aborted) {
					break;
				}
				await new Promise((r) => setTimeout(r, RECONNECT_MS));
			}
		};

		void loop();
		return () => {
			cancelled = true;
			controller.abort();
		};
	}, []);
};
