import type { ApiError } from "./client";
import useCustomToast from "./hooks/useCustomToast";

export const emailPattern = {
  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
  message: "Invalid email address",
};

export const namePattern = {
  value: /^[A-Za-z\s\u00C0-\u017F]{1,30}$/,
  message: "Invalid name",
};

interface PasswordRules {
  minLength: {
    value: number;
    message: string;
  };
  required?: string;
}

export const passwordRules = (isRequired = true): PasswordRules => {
  const rules: PasswordRules = {
    minLength: {
      value: 8,
      message: "Password must be at least 8 characters",
    },
  };

  if (isRequired) {
    rules.required = "Password is required";
  }

  return rules;
};

interface FormValues {
  password?: string;
  new_password?: string;
}

interface ConfirmPasswordRules {
  validate: (value: string) => true | string;
  required?: string;
}

export const confirmPasswordRules = (
  getValues: () => FormValues,
  isRequired = true,
): ConfirmPasswordRules => {
  const rules: ConfirmPasswordRules = {
    validate: (value: string) => {
      const password = getValues().password || getValues().new_password;
      return value === password ? true : "The passwords do not match";
    },
  };

  if (isRequired) {
    rules.required = "Password confirmation is required";
  }

  return rules;
};

interface ErrorDetail {
  msg: string;
}

interface ErrorBody {
  detail?: string | ErrorDetail[];
}

export const handleError = (err: ApiError) => {
  const { showErrorToast } = useCustomToast();

  let errorMessage = "Something went wrong.";

  if (err.body && typeof err.body === "object") {
    const body = err.body as ErrorBody;
    const errDetail = body.detail;

    if (typeof errDetail === "string") {
      errorMessage = errDetail;
    } else if (Array.isArray(errDetail) && errDetail.length > 0) {
      errorMessage = errDetail[0].msg;
    }
  }

  showErrorToast(errorMessage);
};
