import { useFieldArray, useFormContext } from "react-hook-form";
import type { FrappeFormField } from "@/types/response-types";
import { Button } from "@/components/ui/button";
import {
  FieldDescription,
  FieldGroup,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field";
import FormFields from "./fields";
import { emptyRow } from "./values";

export default function TableField({
  field,
  name,
}: {
  field: FrappeFormField;
  name: string;
}) {
  const { control } = useFormContext();
  const { fields, append, remove } = useFieldArray({ control, name });
  const childFields = field.child_fields ?? [];

  return (
    <FieldSet>
      <FieldLegend>{field.label}</FieldLegend>
      {field.description ? (
        <FieldDescription>{field.description}</FieldDescription>
      ) : null}
      {childFields.length === 0 ? (
        <FieldDescription>No editable columns.</FieldDescription>
      ) : (
        <FieldGroup>
          {fields.map((row, index) => (
            <div key={row.id} className="flex flex-col gap-3 rounded-lg border p-3">
              <div className="flex justify-end">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => remove(index)}
                >
                  Remove
                </Button>
              </div>
              <FormFields
                fields={childFields}
                namePrefix={`${name}.${index}`}
              />
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            onClick={() => append(emptyRow(childFields))}
          >
            Add row
          </Button>
        </FieldGroup>
      )}
    </FieldSet>
  );
}
