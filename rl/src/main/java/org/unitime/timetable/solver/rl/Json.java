package org.unitime.timetable.solver.rl;

import java.util.Collection;
import java.util.Map;

/** Minimal JSON writer for metrics and trajectory logs (no external dependency). */
public final class Json {
    private Json() {}

    public static String write(Object o) {
        StringBuilder sb = new StringBuilder();
        write(sb, o);
        return sb.toString();
    }

    @SuppressWarnings("unchecked")
    public static void write(StringBuilder sb, Object o) {
        if (o == null) { sb.append("null"); return; }
        if (o instanceof String) { quote(sb, (String) o); return; }
        if (o instanceof Boolean) { sb.append(o.toString()); return; }
        if (o instanceof Number) {
            double d = ((Number) o).doubleValue();
            if (o instanceof Double || o instanceof Float) {
                if (Double.isNaN(d) || Double.isInfinite(d)) sb.append("null"); else sb.append(o.toString());
            } else sb.append(o.toString());
            return;
        }
        if (o instanceof Map) {
            sb.append('{');
            boolean first = true;
            for (Map.Entry<Object, Object> e: ((Map<Object, Object>) o).entrySet()) {
                if (!first) sb.append(',');
                first = false;
                quote(sb, String.valueOf(e.getKey()));
                sb.append(':');
                write(sb, e.getValue());
            }
            sb.append('}');
            return;
        }
        if (o instanceof Collection) {
            sb.append('[');
            boolean first = true;
            for (Object e: (Collection<Object>) o) {
                if (!first) sb.append(',');
                first = false;
                write(sb, e);
            }
            sb.append(']');
            return;
        }
        if (o instanceof float[]) {
            sb.append('[');
            float[] a = (float[]) o;
            for (int i = 0; i < a.length; i++) { if (i > 0) sb.append(','); sb.append(a[i]); }
            sb.append(']');
            return;
        }
        if (o instanceof double[]) {
            sb.append('[');
            double[] a = (double[]) o;
            for (int i = 0; i < a.length; i++) { if (i > 0) sb.append(','); write(sb, a[i]); }
            sb.append(']');
            return;
        }
        if (o instanceof long[]) {
            sb.append('[');
            long[] a = (long[]) o;
            for (int i = 0; i < a.length; i++) { if (i > 0) sb.append(','); sb.append(a[i]); }
            sb.append(']');
            return;
        }
        if (o instanceof int[]) {
            sb.append('[');
            int[] a = (int[]) o;
            for (int i = 0; i < a.length; i++) { if (i > 0) sb.append(','); sb.append(a[i]); }
            sb.append(']');
            return;
        }
        if (o instanceof boolean[]) {
            sb.append('[');
            boolean[] a = (boolean[]) o;
            for (int i = 0; i < a.length; i++) { if (i > 0) sb.append(','); sb.append(a[i]); }
            sb.append(']');
            return;
        }
        quote(sb, o.toString());
    }

    private static void quote(StringBuilder sb, String s) {
        sb.append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default:
                    if (c < 0x20) sb.append(String.format("\\u%04x", (int) c)); else sb.append(c);
            }
        }
        sb.append('"');
    }
}
