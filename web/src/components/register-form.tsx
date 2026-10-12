"use client";

import { useActionState } from "react";

import { register } from "@/lib/actions";

import { Alert, Button, Field } from "./ui";

export function RegisterForm() {
  const [state, action, pending] = useActionState(register, {});
  return (
    <form action={action} className="space-y-4">
      {state.error && <Alert>{state.error}</Alert>}
      <div className="grid grid-cols-2 gap-3">
        <Field
          label="First name"
          name="first_name"
          autoComplete="given-name"
          required
          defaultValue={state.values?.first_name}
          error={state.fieldErrors?.first_name}
        />
        <Field
          label="Last name"
          name="last_name"
          autoComplete="family-name"
          required
          defaultValue={state.values?.last_name}
          error={state.fieldErrors?.last_name}
        />
      </div>
      <Field
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        required
        defaultValue={state.values?.email}
        error={state.fieldErrors?.email}
      />
      <Field
        label="Password"
        name="password"
        type="password"
        autoComplete="new-password"
        minLength={8}
        maxLength={72}
        required
        error={state.fieldErrors?.password}
      />
      <Button type="submit" disabled={pending} className="w-full">
        {pending ? "Creating account…" : "Create account"}
      </Button>
    </form>
  );
}
