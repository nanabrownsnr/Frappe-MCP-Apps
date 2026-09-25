import { Controller, useFormContext, useWatch } from "react-hook-form";
import type { FrappeFormField } from "@/types/response-types";
import { Switch } from "@/components/ui/switch";
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  NativeSelect,
  NativeSelectOption,
} from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";
import TableField from "./table-field";
import {
  docAtPrefix,
  fieldDescription,
  isFieldRequired,
  isFieldVisible,
  selectOptions,
  type FormValues,
} from "./values";

export default function FormFields({
  fields,
  namePrefix,
}: {
  fields: FrappeFormField[];
  namePrefix?: string;
}) {
  const values = useWatch() as FormValues;
  const doc = docAtPrefix(values, namePrefix);

  return fields.map((field) => {
    if (!isFieldVisible(field.depends_on, doc)) return null;
    const name = namePrefix
      ? `${namePrefix}.${field.fieldname}`
      : field.fieldname;
    if (field.fieldtype === "Table") {
      return <TableField key={name} field={field} name={name} />;
    }
    return (
      <ScalarField
        key={name}
        field={field}
        name={name}
        required={isFieldRequired(field, doc)}
      />
    );
  });
}

function ScalarField({
  field,
  name,
  required,
}: {
  field: FrappeFormField;
  name: string;
  required: boolean;
}) {
  const { control } = useFormContext();
  const description = fieldDescription(field);
  const inputId = name.replaceAll(".", "-");

  return (
    <Controller
      control={control}
      name={name}
      rules={{
        required: required ? `${field.label} is required` : false,
      }}
      render={({ field: input, fieldState }) => {
        const invalid = fieldState.invalid || undefined;
        const error = <FieldError errors={[fieldState.error]} />;

        if (field.fieldtype === "Check") {
          return (
            <Field orientation="horizontal" data-invalid={invalid}>
              <FieldContent>
                <FieldLabel htmlFor={inputId}>
                  {field.label}
                  {required ? <RequiredMark /> : null}
                </FieldLabel>
                {error}
              </FieldContent>
              <Switch
                id={inputId}
                checked={Boolean(input.value)}
                onCheckedChange={input.onChange}
                onBlur={input.onBlur}
                aria-invalid={invalid}
              />
            </Field>
          );
        }

        return (
          <Field data-invalid={invalid}>
            <FieldLabel htmlFor={inputId}>
              {field.label}
              {required ? <RequiredMark /> : null}
            </FieldLabel>
            {field.fieldtype === "Select" ||
            (field.fieldtype === "Link" && !!field.choices?.length) ? (
              <NativeSelect
                id={inputId}
                className="w-full"
                value={String(input.value ?? "")}
                onChange={input.onChange}
                onBlur={input.onBlur}
                aria-invalid={invalid}
              >
                <NativeSelectOption value="">
                  {required ? "Select" : "None"}
                </NativeSelectOption>
                {field.fieldtype === "Link"
                  ? field.choices?.map((choice) => (
                      <NativeSelectOption
                        key={choice.value}
                        value={choice.value}
                      >
                        {choice.label}
                      </NativeSelectOption>
                    ))
                  : selectOptions(field.options).map((option) => (
                      <NativeSelectOption key={option} value={option}>
                        {option}
                      </NativeSelectOption>
                    ))}
              </NativeSelect>
            ) : field.fieldtype === "Small Text" ||
              field.fieldtype === "Text" ? (
              <Textarea
                id={inputId}
                value={String(input.value ?? "")}
                onChange={input.onChange}
                onBlur={input.onBlur}
                aria-invalid={invalid}
              />
            ) : (
              <Input
                id={inputId}
                type={inputType(field.fieldtype)}
                step={
                  field.fieldtype === "Currency" ||
                  field.fieldtype === "Percent" ||
                  field.fieldtype === "Float"
                    ? "any"
                    : undefined
                }
                value={String(input.value ?? "")}
                onChange={input.onChange}
                onBlur={input.onBlur}
                aria-invalid={invalid}
              />
            )}
            {description ? (
              <FieldDescription>{description}</FieldDescription>
            ) : null}
            {error}
          </Field>
        );
      }}
    />
  );
}

function RequiredMark() {
  return <span className="text-destructive"> *</span>;
}

function inputType(fieldtype: FrappeFormField["fieldtype"]) {
  if (fieldtype === "Date") return "date";
  if (fieldtype === "Datetime") return "datetime-local";
  if (
    fieldtype === "Currency" ||
    fieldtype === "Percent" ||
    fieldtype === "Float"
  ) {
    return "number";
  }
  return "text";
}
