import nextCore from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

export default [
    {
        ignores: ["node_modules/**", ".next/**", "out/**"],
    },
    ...nextCore,
    ...nextTypescript,
];
