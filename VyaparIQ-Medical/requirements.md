# VyaparIQ Medical Edition - Requirements Document

## Project Overview
**Project Name:** VyaparIQ Medical Edition  
**Description:** An AI-powered inventory and safety management system for medical stores and pharmacies in India. Uses computer vision and natural language processing to automate stock management, expiry tracking, and drug safety checks.

## Problem Statement
Medical stores in India face critical challenges:
- **30% of medicines expire unused** due to poor inventory tracking
- **Handwritten prescription-based ordering** is error-prone and time-consuming
- **No automated system** to check drug interactions or contraindications
- Results in significant financial losses and potential patient safety risks

## Target Users
- **Small medical store owners (chemists)** managing 500-2000 SKUs
- **Pharmacy managers** in tier 2/3 cities
- **ASHA workers** managing village-level medicine stocks

## Functional Requirements

### 1. Visual Inventory Audit
**Input:** Photo of medical store shelf  
**Process:** AI identifies medicines by packaging, counts stock levels, detects missing essential drugs  
**Output:** JSON list of medicines detected, stock levels, and reorder recommendations  
**Edge Cases:** Handle partially visible labels, regional language packaging

**Business Logic:**
- Detect medicine name, brand, and quantity from packaging
- Compare against essential medicines list
- Generate reorder recommendations based on stock levels

### 2. Expiry Date Intelligence
**Input:** Photo of medicine strips/bottles showing expiry dates  
**Process:** OCR extraction + date parsing, calculate days until expiry  
**Output:** Alert for medicines expiring in next 30/60/90 days with priority ranking

**Business Logic:**
- Medicines <30 days = urgent discount/return (RED priority)
- Medicines 30-90 days = normal sale priority (YELLOW priority)
- Medicines >90 days = standard stock (GREEN priority)

### 3. Prescription-to-Order Automation
**Input:** Photo of handwritten doctor prescription  
**Process:** Extract medicine names (handle common abbreviations like "Tab" for tablets), dosage, quantity  
**Output:** Auto-generated purchase order list with generic alternatives suggested  
**Safety:** Flag if prescribed combination has known drug interactions

**Supported Abbreviations:**
- Tab = Tablets
- Cap = Capsules
- Syr = Syrup
- Inj = Injection

### 4. Drug Safety Checker
**Input:** List of medicines being restocked  
**Process:** Cross-reference against known drug interaction database (loaded as RAG)  
**Output:** Warning messages like "Aspirin + Warfarin = bleeding risk"  
**Data Source:** Synthetic drug interaction database

**Severity Levels:**
- CRITICAL: Contraindicated combination
- HIGH: Major interaction risk
- MODERATE: Monitor patient closely
- LOW: Minor interaction

### 5. Dashboard & Analytics
**Mobile-first UI showing:**
- Stock status (color-coded: red=low, yellow=moderate, green=sufficient)
- Expiry timeline (calendar view)
- Revenue impact (saved money from preventing expiry)
- Weekly insights: "You saved ₹5,000 this week by selling near-expiry stock first"

## Non-Functional Requirements

### Performance
- **Response time:** <3 seconds for image analysis
- **Accuracy:** 95%+ for OCR on clear medicine packaging
- **Availability:** 99% uptime for demo

### Cost
- **Target:** <₹2 per 100 API calls (AWS Free Tier optimized)
- **Total AWS cost:** <$5 for entire hackathon

### Language Support
- English + Hindi support for UI
- Regional language packaging recognition

### Offline Capability
- Core dashboard works offline
- Syncs when online connection available

## Success Metrics for Demo
- Detect 8/10 medicines correctly from shelf photo
- Extract 4/5 medicine names from handwritten prescription
- Flag 2 known drug interactions from safety checker
- Show dashboard with live data update in <3 seconds

## Constraints
- Must use AWS Free Tier services only
- Must work with synthetic/staged photos (no real medical store access required)
- Bedrock API rate limits: max 20 requests/minute on free tier
- No real patient data (use synthetic test data only)

## Security & Compliance
- All images deleted after 24 hours (S3 lifecycle policy)
- No real patient data stored
- Disclaimers: "This is an inventory management tool, not medical advice"
- Clear limitation statements in UI

## Limitations
- Currently uses synthetic data (not validated with real medical stores)
- OCR accuracy depends on image quality (needs good lighting)
- Drug interaction database is simplified (not comprehensive medical-grade)
- Hindi language support is basic (not full localization)
- No integration with existing billing software (future scope)

## Future Roadmap
- Voice interface for low-literacy users
- Integration with government drug price API
- Barcode scanning for faster input
- Supplier integration for automated ordering
- Predictive analytics (forecast demand based on seasonal trends)
- Mobile app (React Native) for better camera UX