import { useEffect, useRef, useState } from "react";

const useDebouncedValue = <T>(value: T, delayMs: number) => {
	const [debouncedValue, setDebouncedValue] = useState(value);

	useEffect(() => {
		const timer = window.setTimeout(() => setDebouncedValue(value), delayMs);
		return () => window.clearTimeout(timer);
	}, [value, delayMs]);

	return debouncedValue;
};

export const useDiagnosisFilters = (onDebouncedChange?: () => void) => {
	const [patientId, setPatientId] = useState("");
	const [patientName, setPatientName] = useState("");
	const debouncedPatientId = useDebouncedValue(patientId, 500);
	const debouncedPatientName = useDebouncedValue(patientName, 500);

	const isFirstDebounced = useRef(true);
	useEffect(() => {
		if (isFirstDebounced.current) {
			isFirstDebounced.current = false;
			return;
		}
		onDebouncedChange?.();
	}, [debouncedPatientId, debouncedPatientName, onDebouncedChange]);

	const resetFilters = () => {
		setPatientId("");
		setPatientName("");
	};

	return {
		patientId,
		patientName,
		debouncedPatientId,
		debouncedPatientName,
		setPatientId,
		setPatientName,
		resetFilters,
	};
};
