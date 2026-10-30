"""Briefing matinal — compile les agendas Google de Pat et envoie le déroulé du jour par email.

Le workflow lit les événements de la journée dans ses agendas Google Calendar,
les met en forme, puis envoie le déroulé par email sur son adresse perso
(notification relayée sur sa montre Garmin via le téléphone).
"""

from datetime import timedelta
from typing import Any

import mistralai.workflows as workflows
from mistralai.workflows import Depends
from mistralai.workflows.plugins.mistralai.connectors import (
    ToolCallClient,
    connector,
    uses_connectors,
)

PARIS_TZ = "Europe/Paris"
RECIPIENT = "coupelatomate@gmail.com"

# Agendas à compiler : (libellé, calendarId — None = agenda principal)
CALENDARS: list[tuple[str, str | None]] = [
    ("Perso", None),
    ("Famille", "family01900525752157566170@group.calendar.google.com"),
    ("Pat et Aurélie", "d8fe0f457f9ff3be9a06cb1d6aa910303bccdbdb21be5543dd3a0376260ba5ff@group.calendar.google.com"),
    ("SEGPA", "brcak9omqj5d83i8j2s0r42ie8@group.calendar.google.com"),
    ("Mairie", "q71kovtrkq9e1h5i82kei5aue8@group.calendar.google.com"),
]

gcal = connector("google_calendar", run_as="deployment")
gmail = connector("gmail", run_as="deployment")


def _as_dict(res: Any) -> dict:
    """Normalise la réponse brute d'un appel d'outil connecteur en dict."""
    if isinstance(res, dict):
        return res
    if hasattr(res, "model_dump"):
        return res.model_dump()
    if hasattr(res, "__dict__"):
        return dict(res.__dict__)
    return {}


@workflows.activity(name="collecter-evenements", start_to_close_timeout=timedelta(minutes=5))
async def collecter_evenements(gcal_client: ToolCallClient = Depends(gcal)) -> list[dict]:
    """Lit les événements du jour dans tous les agendas configurés."""
    all_events: list[dict] = []
    for label, cal_id in CALENDARS:
        args: dict[str, Any] = {
            "timeZone": PARIS_TZ,
            "pageSize": 50,
            "orderBy": "startTime",
        }
        if cal_id:
            args["calendarId"] = cal_id
        res = _as_dict(await gcal_client.call_tool(tool_name="list_events", arguments=args))
        for ev in res.get("events", []) or []:
            if isinstance(ev, dict):
                ev = dict(ev)
                ev["_calendrier"] = label
                all_events.append(ev)
    # Tri chronologique (les événements sans heure passent en premier)
    def _key(e: dict) -> str:
        s = e.get("start") or {}
        return str(s.get("dateTime") or s.get("date") or "")
    all_events.sort(key=_key)
    return all_events


def _format_heure(e: dict) -> str:
    s = e.get("start") or {}
    dt = s.get("dateTime")
    if not dt:
        return "journée"
    return dt[11:16]  # "HH:MM"


def _format_html(events: list[dict], titre_jour: str) -> str:
    lignes = []
    for e in events:
        heure = _format_heure(e)
        titre = e.get("summary") or "(sans titre)"
        cal = e.get("_calendrier", "")
        lieu = e.get("location")
        detail = f" — {lieu}" if lieu else ""
        lignes.append(f"<li><b>{heure}</b> · {titre}<span style='color:#888'> [{cal}]{detail}</span></li>")
    corps = "".join(lignes) if lignes else "<li style='color:#888'>Aucun événement aujourd'hui 🎉</li>"
    return (
        "<div style='font-family:sans-serif'>"
        f"<h2>📋 Déroulé de ta journée — {titre_jour}</h2>"
        f"<ul style='line-height:1.6'>{corps}</ul>"
        "<p style='color:#888;font-size:small'>Briefing automatique 6h20 — agendas Google compilés par Vibe.</p>"
        "</div>"
    )


@workflows.activity(name="envoyer-briefing", start_to_close_timeout=timedelta(minutes=2))
async def envoyer_briefing(subject: str, html: str, gmail_client: ToolCallClient = Depends(gmail)) -> None:
    await gmail_client.call_tool(
        tool_name="send_email",
        arguments={"to": [RECIPIENT], "subject": subject, "htmlBody": html},
    )


@workflows.workflow.define(
    name="briefing-matin",
    workflow_display_name="Briefing du matin",
    workflow_description="Compile les agendas Google de la journée et envoie le déroulé par email à 6h20.",
)
@uses_connectors(gcal, gmail)
class BriefingMatin:
    @workflows.workflow.entrypoint
    async def run(self, date_iso: str | None = None) -> dict:
        events = await collecter_evenements()
        titre = date_iso or "aujourd'hui"
        subject = "📋 PROGRAMME DU JOUR"
        html = _format_html(events, titre)
        await envoyer_briefing(subject, html)
        return {"envoye": True, "nombre_evenements": len(events)}
