import { useCallback, useState } from "react";

/**
 * 患者ID・氏名は入力欄の値と API に渡す値を分離し、明示的な確定（Enter）まで検索しない。
 */
export const useDiagnosisFilters = (onCommitted?: () => void) => {
	const [patientIdInput, setPatientIdInput] = useState("");
	const [patientNameInput, setPatientNameInput] = useState("");
	const [committedPatientId, setCommittedPatientId] = useState("");
	const [committedPatientName, setCommittedPatientName] = useState("");

	const commitPatientFilters = useCallback(() => {
		setCommittedPatientId(patientIdInput);
		setCommittedPatientName(patientNameInput);
		onCommitted?.();
	}, [patientIdInput, patientNameInput, onCommitted]);

	return {
		patientIdInput,
		patientNameInput,
		committedPatientId,
		committedPatientName,
		setPatientIdInput,
		setPatientNameInput,
		commitPatientFilters,
	};
};
