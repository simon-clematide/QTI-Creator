package org.qticreator.validator;

import java.io.File;
import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Enumeration;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

import uk.ac.ed.ph.jqtiplus.SimpleJqtiFacade;
import uk.ac.ed.ph.jqtiplus.notification.Notification;
import uk.ac.ed.ph.jqtiplus.validation.ItemValidationResult;
import uk.ac.ed.ph.jqtiplus.validation.TestValidationResult;
import uk.ac.ed.ph.jqtiplus.xmlutils.locators.FileResourceLocator;

/**
 * Headless QTI 2.1 validator using OpenOLAT's jqtiplus library.
 */
public class QtiValidator {

    public static class ValidationError {
        public final String file;
        public final String message;

        public ValidationError(String file, String message) {
            this.file = file;
            this.message = message;
        }

        @Override
        public String toString() {
            return "[" + file + "] " + message;
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            System.err.println("Usage: java QtiValidator [--json] <file.xml|package.zip> ...");
            System.exit(2);
        }

        boolean jsonMode = false;
        List<String> targetPaths = new ArrayList<>();
        for (String arg : args) {
            if ("--json".equals(arg)) {
                jsonMode = true;
            } else {
                targetPaths.add(arg);
            }
        }

        SimpleJqtiFacade facade = new SimpleJqtiFacade();
        FileResourceLocator locator = new FileResourceLocator();
        List<ValidationError> errors = new ArrayList<>();
        int validatedFilesCount = 0;

        for (String targetPath : targetPaths) {
            File f = new File(targetPath);
            if (!f.exists()) {
                errors.add(new ValidationError(targetPath, "File does not exist"));
                continue;
            }

            if (f.getName().endsWith(".zip")) {
                Path tempDir = Files.createTempDirectory("jqti_validate_");
                try (ZipFile zf = new ZipFile(f)) {
                    Enumeration<? extends ZipEntry> entries = zf.entries();
                    while (entries.hasMoreElements()) {
                        ZipEntry entry = entries.nextElement();
                        File dest = new File(tempDir.toFile(), entry.getName());
                        if (entry.isDirectory()) {
                            dest.mkdirs();
                        } else {
                            dest.getParentFile().mkdirs();
                            Files.copy(zf.getInputStream(entry), dest.toPath());
                        }
                    }

                    File[] files = tempDir.toFile().listFiles((dir, name) -> name.endsWith(".xml"));
                    if (files != null) {
                        for (File xmlFile : files) {
                            String relName = f.getName() + " -> " + xmlFile.getName();
                            if (xmlFile.getName().startsWith("item_")) {
                                validatedFilesCount++;
                                validateItem(facade, locator, xmlFile, relName, errors);
                            } else if (xmlFile.getName().equals("Test.xml")) {
                                validatedFilesCount++;
                                validateTest(facade, locator, xmlFile, relName, errors);
                            }
                        }
                    }
                } finally {
                    Files.walk(tempDir)
                            .sorted(Comparator.reverseOrder())
                            .map(Path::toFile)
                            .forEach(File::delete);
                }
            } else if (f.getName().endsWith(".xml")) {
                validatedFilesCount++;
                if (f.getName().startsWith("item_") || f.getName().contains("item")) {
                    validateItem(facade, locator, f, f.getName(), errors);
                } else if (f.getName().equals("Test.xml") || f.getName().contains("test")) {
                    validateTest(facade, locator, f, f.getName(), errors);
                } else {
                    validateItem(facade, locator, f, f.getName(), errors);
                }
            }
        }

        if (jsonMode) {
            StringBuilder sb = new StringBuilder();
            sb.append("{\n");
            sb.append("  \"valid\": ").append(errors.isEmpty()).append(",\n");
            sb.append("  \"validatedCount\": ").append(validatedFilesCount).append(",\n");
            sb.append("  \"errors\": [\n");
            for (int i = 0; i < errors.size(); i++) {
                ValidationError err = errors.get(i);
                sb.append("    {\"file\": \"")
                  .append(escapeJson(err.file))
                  .append("\", \"message\": \"")
                  .append(escapeJson(err.message))
                  .append("\"}");
                if (i < errors.size() - 1) sb.append(",");
                sb.append("\n");
            }
            sb.append("  ]\n");
            sb.append("}\n");
            System.out.print(sb.toString());
        } else {
            if (errors.isEmpty()) {
                System.out.println("OK: " + validatedFilesCount + " QTI object(s) validated successfully with 0 errors.");
            } else {
                System.err.println("FAILED: " + errors.size() + " validation error(s) found in " + validatedFilesCount + " file(s):");
                for (ValidationError err : errors) {
                    System.err.println("  - " + err);
                }
            }
        }

        if (!errors.isEmpty()) {
            System.exit(1);
        }
    }

    private static void validateItem(SimpleJqtiFacade facade, FileResourceLocator locator, File file, String relName, List<ValidationError> errors) {
        try {
            ItemValidationResult res = facade.loadResolveAndValidateItem(locator, file.toURI());
            if (!res.isValid() || res.hasModelValidationErrors()) {
                for (Notification n : res.getModelValidationErrors()) {
                    errors.add(new ValidationError(relName, n.getMessage()));
                }
            }
        } catch (Exception e) {
            errors.add(new ValidationError(relName, "Exception during item validation: " + e.getMessage()));
        }
    }

    private static void validateTest(SimpleJqtiFacade facade, FileResourceLocator locator, File file, String relName, List<ValidationError> errors) {
        try {
            TestValidationResult res = facade.loadResolveAndValidateTest(locator, file.toURI());
            if (!res.isValid() || res.hasModelValidationErrors()) {
                for (Notification n : res.getModelValidationErrors()) {
                    errors.add(new ValidationError(relName, n.getMessage()));
                }
            }
        } catch (Exception e) {
            errors.add(new ValidationError(relName, "Exception during test validation: " + e.getMessage()));
        }
    }

    private static String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }
}
