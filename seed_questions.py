from app import app, db
from models import Question, Classifier, QuestionClassifier
from quiz_data import CLASSIFIERS, QUESTIONS


def seed():
    classifier_map = {}
    for name, bidirectional in CLASSIFIERS:
        obj = Classifier.query.filter_by(name=name).first()
        if not obj:
            obj = Classifier(name=name, bidirectional=bidirectional)
            db.session.add(obj)
    db.session.commit()

    for name, _ in CLASSIFIERS:
        classifier_map[name] = Classifier.query.filter_by(name=name).first()

    for text, loadings in QUESTIONS:
        if not Question.query.filter_by(text=text).first():
            q = Question(text=text)
            db.session.add(q)
            db.session.flush()
            for classifier_name, weight, positive in loadings:
                db.session.add(QuestionClassifier(
                    question_id=q.id,
                    classifier_id=classifier_map[classifier_name].id,
                    weight=weight,
                    positive=positive,
                ))

    db.session.commit()
    print(f"Seeded {len(CLASSIFIERS)} classifiers and {len(QUESTIONS)} questions.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed()
