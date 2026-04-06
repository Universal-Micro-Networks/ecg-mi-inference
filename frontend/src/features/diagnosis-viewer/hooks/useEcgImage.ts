import { useEffect, useState } from "react";

import { apiFetch } from "../../../lib/auth";

export const useEcgImage = (examinationId: string, cacheKey = 0) => {
	const [imageUrl, setImageUrl] = useState<string | null>(null);
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!examinationId) {
			return;
		}

		let objectUrl: string | null = null;
		const controller = new AbortController();

		const fetchImage = async () => {
			try {
				setIsLoading(true);
				setError(null);
				const qs = cacheKey ? `?v=${encodeURIComponent(String(cacheKey))}` : "";
				const response = await apiFetch(
					`/api/examinations/${examinationId}/ecg-image${qs}`,
					{
						signal: controller.signal,
					},
				);

				if (response.status === 404) {
					setImageUrl(null);
					return;
				}

				if (!response.ok) {
					throw new Error("心電図画像の取得に失敗しました");
				}

				const blob = await response.blob();
				objectUrl = URL.createObjectURL(blob);
				setImageUrl(objectUrl);
			} catch (fetchError) {
				if (
					fetchError instanceof DOMException &&
					fetchError.name === "AbortError"
				) {
					return;
				}
				setError("心電図画像の取得に失敗しました");
			} finally {
				setIsLoading(false);
			}
		};

		fetchImage();

		return () => {
			controller.abort();
			if (objectUrl) {
				URL.revokeObjectURL(objectUrl);
			}
		};
	}, [examinationId, cacheKey]);

	return { imageUrl, isLoading, error };
};
