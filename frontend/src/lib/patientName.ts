export const formatPatientName = (rawName: string): string => {
	const name = rawName.trim();
	if (!name.includes("^")) {
		return name;
	}

	const [leftRaw, rightRaw] = name.split("^", 2);
	const left = leftRaw.trim();
	const right = rightRaw.trim();

	if (!right || left === right) {
		return left;
	}
	return `${left} （${right}）`;
};
