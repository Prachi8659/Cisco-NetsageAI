/**
 * Formats API and runtime errors into clean, user-friendly strings.
 * Prevents raw FastAPI/Pydantic validation objects ({type, loc, msg, input, ctx})
 * from being passed directly to React JSX children.
 */
export function formatApiError(err: unknown, fallbackMessage = 'An unexpected error occurred.'): string {
  if (!err) return fallbackMessage;

  // If already a string
  if (typeof err === 'string') {
    return err.trim() || fallbackMessage;
  }

  // Handle Axios or HTTP response error objects
  if (typeof err === 'object' && err !== null) {
    const errorObj = err as Record<string, any>;
    const responseData = errorObj.response?.data;

    if (responseData) {
      const detail = responseData.detail;

      // 1. String detail (e.g. HTTPException(status_code=400, detail="Invalid file type"))
      if (typeof detail === 'string') {
        return detail;
      }

      // 2. Pydantic / FastAPI validation error array (HTTP 422)
      // e.g. [{ type: 'missing', loc: ['body', 'title'], msg: 'Field required', input: null, ctx: {} }]
      if (Array.isArray(detail)) {
        const messages = detail
          .map((item: any) => {
            if (typeof item === 'string') return item;
            if (typeof item === 'object' && item !== null) {
              const locArray = Array.isArray(item.loc) ? item.loc : [item.loc];
              // Filter out 'body' prefix from location
              const fieldParts = locArray.filter((part: any) => part !== 'body' && part !== undefined && part !== null);
              const fieldName = fieldParts.join('.');
              const msg = item.msg || item.message || 'Invalid value';
              return fieldName ? `${fieldName}: ${msg}` : msg;
            }
            return null;
          })
          .filter(Boolean);

        if (messages.length > 0) {
          return messages.join(' | ');
        }
      }

      // 3. Single object detail
      if (typeof detail === 'object' && detail !== null) {
        if (detail.msg) return String(detail.msg);
        if (detail.message) return String(detail.message);
        if (detail.error) return String(detail.error);
      }

      // 4. Other root properties in responseData
      if (typeof responseData.message === 'string') return responseData.message;
      if (typeof responseData.error === 'string') return responseData.error;
    }

    // Standard JavaScript / Axios Error message
    if (typeof errorObj.message === 'string' && errorObj.message.trim()) {
      if (errorObj.message.includes('Network Error')) {
        return 'Unable to connect to the NetSage backend server. Please verify the backend is running.';
      }
      return errorObj.message;
    }
  }

  return fallbackMessage;
}
