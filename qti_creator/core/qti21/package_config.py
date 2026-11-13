"""OpenOLAT native QTI21PackageConfig.xml generator.

Rule: OpenOLAT requires QTI21PackageConfig.xml in the package root to immediately
recognize the test as native and allow direct editing in the OpenOLAT test editor.
"""


def generate_package_config_xml() -> str:
    """Generate the standard OpenOLAT QTI21PackageConfig.xml delivery options."""
    return """<deliveryOptions>
  <enableCancel>false</enableCancel>
  <enableSuspend>false</enableSuspend>
  <displayScoreProgress>false</displayScoreProgress>
  <displayQuestionProgress>false</displayQuestionProgress>
  <displayMaxScoreItem>true</displayMaxScoreItem>
  <showMenu>true</showMenu>
  <showTitles>true</showTitles>
  <personalNotes>false</personalNotes>
  <hideLms>true</hideLms>
  <hideFeedbacks>false</hideFeedbacks>
  <blockAfterSuccess>false</blockAfterSuccess>
  <maxAttempts>0</maxAttempts>
  <allowAnonym>false</allowAnonym>
  <digitalSignature>false</digitalSignature>
  <digitalSignatureMail>false</digitalSignatureMail>
  <showAssessmentResultsOnFinish>false</showAssessmentResultsOnFinish>
  <enableAssessmentItemBack>false</enableAssessmentItemBack>
  <enableAssessmentItemResetHard>false</enableAssessmentItemResetHard>
  <enableAssessmentItemResetSoft>false</enableAssessmentItemResetSoft>
  <enableAssessmentItemSkip>false</enableAssessmentItemSkip>
  <assessmentResultsOptions>
    <metadata>false</metadata>
    <sectionSummary>false</sectionSummary>
    <questionSummary>false</questionSummary>
    <userSolutions>false</userSolutions>
    <correctSolutions>false</correctSolutions>
    <questions>false</questions>
  </assessmentResultsOptions>
  <chatCoaches>false</chatCoaches>
  <chatOwners>false</chatOwners>
  <canStartChat>false</canStartChat>
  <pageMode>false</pageMode>
  <lastQuestion>false</lastQuestion>
</deliveryOptions>"""
