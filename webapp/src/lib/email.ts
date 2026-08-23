import nodemailer from "nodemailer";

const transporter = process.env.SMTP_HOST
  ? nodemailer.createTransport({
      host: process.env.SMTP_HOST,
      port: Number(process.env.SMTP_PORT || 587),
      secure: process.env.SMTP_SECURE === "true",
      auth: {
        user: process.env.SMTP_USER,
        pass: process.env.SMTP_PASS,
      },
    })
  : null;

export async function sendEmail(opts: { to: string; subject: string; html: string }) {
  if (transporter) {
    await transporter.sendMail({
      from: process.env.SMTP_FROM || "MigratorGen <noreply@migratorgen.dev>",
      to: opts.to,
      subject: opts.subject,
      html: opts.html,
    });
  } else {
    console.log("═══════════════════════════════════════════════════════════════");
    console.log("EMAIL (no SMTP configured — logging to console)");
    console.log("To:", opts.to);
    console.log("Subject:", opts.subject);
    console.log("Body:");
    console.log(opts.html.replace(/<[^>]+>/g, ""));
    console.log("═══════════════════════════════════════════════════════════════");
  }
}
