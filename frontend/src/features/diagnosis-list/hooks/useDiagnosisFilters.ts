import { useEffect, useMemo, useState } from "react";
import type { ExaminationSummary } from "../types";

const useDebouncedValue = <T>(value: T, delayMs: number) => {
	const [debouncedValue, setDebouncedValue] = useState(value);

	useEffect(() => {
		const timer = window.setTimeout(() => setDebouncedValue(value), delayMs);
		return () => window.clearTimeout(timer);
	}, [value, delayMs]);

	return debouncedValue;
};

export const useDiagnosisFilters = (data: ExaminationSummary[]) => {
	const [patientId, setPatientId] = useState("");
	const [patientName, setPatientName] = useState("");
	const debouncedPatientId = useDebouncedValue(patientId, 500);
	const debouncedPatientName = useDebouncedValue(patientName, 500);

	const filtered = useMemo(() => {
		const idKeyword = debouncedPatientId.trim().toLowerCase();
		const nameKeyword = debouncedPatientName.trim().toLowerCase();

		return data.filter((item) => {
			const matchId = idKeyword
				? item.patient.external_id.toLowerCase().includes(idKeyword)
				: true;
			const matchName = nameKeyword
				? item.patient.name.toLowerCase().includes(nameKeyword)
				: true;
			return matchId && matchName;
		});
	}, [data, debouncedPatientId, debouncedPatientName]);

	const resetFilters = () => {
		setPatientId("");
		setPatientName("");
	};

	return {
		patientId,
		patientName,
		setPatientId,
		setPatientName,
		resetFilters,
		filtered,
	};
};
