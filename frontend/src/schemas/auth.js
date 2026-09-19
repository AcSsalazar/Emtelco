import { z } from "zod";

const emailOrIdentification = z
  .string()
  .min(1, "Ingresa tu correo o identificación")
  .refine(
    (value) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value) || /^\d{4,11}$/.test(value),
    "Ingresa un correo válido o tu identificación (4 a 11 dígitos)"
  );

export const loginSchema = z.object({
  email: emailOrIdentification,
  password: z.string().min(1, "Ingresa tu contraseña"),
});

const namePattern = /^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]+$/;

export const registerSchema = z.object({
  identification: z
    .string()
    .regex(/^\d{4,11}$/, "Entre 4 y 11 dígitos numéricos"),
  fullName: z
    .string()
    .min(1, "Ingresa tu nombre")
    .max(100, "Máximo 100 caracteres")
    .regex(namePattern, "Solo letras, espacios, tildes y ñ"),
  phone: z
    .string()
    .regex(/^[36]\d{9}$/, "10 dígitos, debe iniciar en 3 o 6"),
  email: z.string().min(1, "Ingresa tu correo").email("Correo inválido"),
  password: z.string().min(8, "Mínimo 8 caracteres"),
});

export function fieldErrors(parsed) {
  const errors = {};
  for (const issue of parsed.error.issues) {
    const key = issue.path[0];
    if (key && !errors[key]) errors[key] = issue.message;
  }
  return errors;
}

// Live validation for a single field, used while the user types.
export function validateField(schema, key, value) {
  const field = schema.shape?.[key];
  if (!field) return undefined;
  const result = field.safeParse(value);
  return result.success ? undefined : result.error.issues[0].message;
}
