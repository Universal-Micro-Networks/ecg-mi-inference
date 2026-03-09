import { useState } from "react";

export const useRowSelection = () => {
	const [selectedId, setSelectedId] = useState<string | null>(null);

	return {
		selectedId,
		selectRow: setSelectedId,
	};
};
