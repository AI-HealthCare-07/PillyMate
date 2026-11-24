import { useState } from 'react';
import { Button } from '../components/ui/Button.jsx';
import { Field } from '../components/ui/Field.jsx';
import { Logo } from '../components/ui/misc.jsx';
import { AppShell } from '../components/ui/layout.jsx';

const API_URL = '/api/v1/auth';

/** S-01 로그인 및 회원가입 */
export function LoginScreen({ go }) {

  // 1. 화면 상태 관리
  const [isSignup, setIsSignup] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  // 2. 입력값 관리
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [gender, setGender] = useState('');
  const [birthDate, setBirthDate] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [showConsent, setShowConsent] = useState(false);
  const [termsAgreed, setTermsAgreed] = useState(false);
  const [privacyAgreed, setPrivacyAgreed] = useState(false);
  const allAgreed = termsAgreed && privacyAgreed;

  // 생년월일 기준 만 나이 계산
  function calculateAge(value) {
    if (!value) return null;

    const today = new Date();
    const birthday = new Date(value + 'T00:00:00');

    if (Number.isNaN(birthday.getTime()) || birthday > today) {
      return null;
    }

    let age = today.getFullYear() - birthday.getFullYear();

    if (
      today.getMonth() < birthday.getMonth() ||
      (
        today.getMonth() === birthday.getMonth() &&
        today.getDate() < birthday.getDate()
      )
    ) {
      age -= 1;
    }

    return age;
  }

  const age = calculateAge(birthDate);


  // 3. 입력값 검증
  function validate() {
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailPattern.test(email.trim())) {
      return '올바른 이메일을 입력해 주세요.';
    }

    if (password.length < 8) {
      return '비밀번호는 8자 이상이어야 합니다.';
    }

    if (isSignup) {
      if (!allAgreed) {
        return '필수 약관에 동의해 주세요.';
      }

      const passwordPattern =
        /^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[^a-zA-Z0-9]).{8,}$/;

      const phonePattern =
        /^(010-\d{4}-\d{4}|010\d{8}|\+8210\d{8})$/;

      if (email.trim().length > 40) {
        return '이메일은 40자 이하로 입력해 주세요.';
      }

      if (!passwordPattern.test(password)) {
        return '비밀번호에 대문자, 소문자, 숫자, 특수문자를 포함해 주세요.';
      }

      if (!name.trim() || name.trim().length > 20) {
        return '이름을 1~20자로 입력해 주세요.';
      }

      if (!gender) {
        return '성별을 선택해 주세요.';
      }

      if (!birthDate) {
        return '생년월일을 입력해 주세요.';
      }



      if (age === null) {
        return '올바른 생년월일을 입력해 주세요.';
      }

      if (age < 14) {
        return '가입 가능한 연령인지 확인해 주세요.';
      }



      if (!phonePattern.test(phoneNumber.trim())) {
        return '올바른 휴대폰 번호를 입력해 주세요.';
      }
    }

    return '';
  }

  // 4. 로그인 / 회원가입 화면 전환
  function changeMode() {
    setError('');
    setMessage('');
    setPassword('');
    setTermsAgreed(false);
    setPrivacyAgreed(false);

    if (isSignup) {
      setIsSignup(false);
      setShowConsent(false);
    } else {
      setShowConsent(true);
    }
  }

  function continueSignup() {
    if (!allAgreed) return;
    setShowConsent(false);
    setIsSignup(true);
  }

  // 5. 로그인 및 회원가입 요청
  async function handleSubmit(event) {
    event.preventDefault();

    if (loading) return;

    setError('');
    setMessage('');

    const validationError = validate();

    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);

    const endpoint = isSignup ? 'signup' : 'login';

    const requestData = isSignup
      ? {
          email: email.trim(),
          password: password,
          name: name.trim(),
          gender: gender,
          birth_date: birthDate,
          phone_number: phoneNumber.trim(),
        }
      : {
          email: email.trim(),
          password: password,
        };

    try {
      // API 요청 후 응답 기다리기
      const response = await fetch(`${API_URL}/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(requestData),
      });

      // 응답 데이터 읽기
      let data;

      try {
        data = await response.json();
      } catch {
        throw new Error('서버 응답을 확인할 수 없습니다.');
      }

      // 서버 오류 확인
      if (!response.ok) {
        const detail = data.detail;

        const errorMessage =
          typeof detail === 'string'
            ? detail
            : Array.isArray(detail)
              ? detail.map(item => item.msg).join(' / ')
              : '요청 처리에 실패했습니다.';

        throw new Error(errorMessage);
      }

      // 회원가입 또는 로그인 성공 처리
      if (isSignup) {
        setIsSignup(false);
        setPassword('');
        setTermsAgreed(false);
        setPrivacyAgreed(false);
        setMessage('회원가입이 완료되었습니다. 로그인해 주세요.');
      } else {
        if (!data.access_token) {
          throw new Error('로그인 토큰을 받지 못했습니다.');
        }

        sessionStorage.setItem(
          'access_token',
          data.access_token
        );

        go('children');
      }

    } catch (err) {
      setError(
        err instanceof TypeError
          ? '서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.'
          : err.message
      );
    } finally {
      setLoading(false);
    }
  }

  // 6. 모바일 / 데스크톱 버튼
  function renderButtons() {
    return (
      <>
        <Button
          type="submit"
          form="auth-form"
          className="w-full"
          disabled={loading}
        >
          {loading
            ? '처리 중...'
            : isSignup
              ? '회원가입'
              : '로그인'}
        </Button>

        <Button
          type="button"
          variant="secondary"
          className="w-full"
          disabled={loading}
          onClick={changeMode}
        >
          {isSignup
            ? '이미 계정이 있어요'
            : '처음이에요, 가입할게요'}
        </Button>
      </>
    );
  }

  const actions = {
    mobile: renderButtons(),
    desktop: null,
  };


  // 회원가입 전 필수 약관 동의 화면
  if (showConsent) {
    return (
      <AppShell showTabs={false} showTopBar={false}>
        <div className="flex flex-1 flex-col gap-6 px-6 py-12 lg:px-0">
          <Logo size={28} />

          <h1 className="text-28 font-bold">
            서비스 이용 동의
          </h1>

          <p className="text-15 text-muted">
            PillyMate를 이용하기 위해 필수 약관에 동의해 주세요.
          </p>

          <label className="flex items-center gap-3 rounded-lg border border-line bg-surface p-4">
            <input
              type="checkbox"
              className="h-5 w-5 accent-[#10594f]"
              checked={allAgreed}
              onChange={e => {
                setTermsAgreed(e.target.checked);
                setPrivacyAgreed(e.target.checked);
              }}
            />
            <span className="font-bold">전체 동의하기</span>
          </label>

          <div className="flex flex-col gap-4 rounded-lg border border-line p-4">
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                className="h-5 w-5 accent-[#10594f]"
                checked={termsAgreed}
                onChange={e => setTermsAgreed(e.target.checked)}
              />
              <span>[필수] 서비스 이용약관 동의</span>
            </label>

            <details className="text-14 text-muted">
              <summary className="cursor-pointer">
                서비스 이용약관 안내
              </summary>
              <p className="mt-3">
                PillyMate는 처방전과 복약 정보를 관리하는
                서비스입니다. 복약 가이드는 참고용이며
                의료진의 진료나 처방을 대신하지 않습니다.
              </p>
            </details>

            <label className="flex items-start gap-3 border-t border-line pt-4">
              <input
                type="checkbox"
                className="h-5 w-5 accent-[#10594f]"
                checked={privacyAgreed}
                onChange={e => setPrivacyAgreed(e.target.checked)}
              />
              <span>[필수] 개인정보 수집·이용 동의</span>
            </label>

            <details className="text-14 text-muted">
              <summary className="cursor-pointer">
                개인정보 수집·이용 내용 보기
              </summary>

              <div className="mt-3 flex flex-col gap-3">
                <p>
                  수집 항목: 이메일, 비밀번호, 이름,
                  성별, 생년월일, 휴대폰 번호
                </p>
                <p>
                  이용 목적: 회원 식별, 연령 확인,
                  계정 관리
                </p>
                <p>
                  보유 기간: 회원 탈퇴 시까지
                  (법령상 보존 의무가 있는 경우 제외)
                </p>
                <p>
                  동의를 거부할 수 있으나,
                  필수 정보 수집에 동의하지 않으면
                  회원가입이 제한됩니다.
                </p>
              </div>
            </details>
          </div>

          <Button
            type="button"
            className="w-full"
            disabled={!allAgreed}
            onClick={continueSignup}
          >
            동의하고 계속하기
          </Button>

          <Button
            type="button"
            variant="secondary"
            className="w-full"
            onClick={() => {
              setShowConsent(false);
              setTermsAgreed(false);
              setPrivacyAgreed(false);
            }}
          >
            로그인으로 돌아가기
          </Button>
        </div>
      </AppShell>
    );
  }

  // 7. 화면 표시
  return (
    <AppShell
      showTabs={false}
      showTopBar={false}
      actions={actions}
    >
      <form
        id="auth-form"
        noValidate
        className="flex flex-1 flex-col gap-9 px-6 pb-6 pt-12 lg:justify-center lg:px-0"
        onSubmit={handleSubmit}
      >
        <Logo size={28} />

        <div className="flex flex-col gap-3">
          {isSignup ? (
            <>
              <h1 className="text-28 font-bold">
                회원가입
              </h1>

              <p className="text-15 text-muted">
                PillyMate와 함께 아이의 복약을 관리해 보세요.
              </p>
            </>
          ) : (
            <>
              <h1 className="text-28 font-bold">
                처방전 한 장이면<br />
                아이 약 먹이는 법이<br />
                정리돼요
              </h1>

              <p className="text-15 text-muted">
                사진을 올리면 약 이름과 양을 읽고,
                보호자가 확인한 내용으로 복약 가이드를 만들어요.
              </p>
            </>
          )}
        </div>

        <div className="flex flex-col gap-4">

          <Field
            label="이메일"
            type="email"
            autoComplete="email"
            placeholder="parent@example.com"
            value={email}
            disabled={loading}
            onChange={e => setEmail(e.target.value)}
          />

          <Field
            label="비밀번호"
            type="password"
            autoComplete={
              isSignup ? 'new-password' : 'current-password'
            }
            helper={
              isSignup
                ? '8자 이상, 대문자·소문자·숫자·특수문자를 포함해 주세요.'
                : '8자 이상 입력해 주세요.'
            }
            value={password}
            disabled={loading}
            onChange={e => setPassword(e.target.value)}
          />

          {isSignup && (
            <>
              <Field
                label="이름"
                placeholder="이름을 입력해 주세요"
                value={name}
                maxLength={20}
                disabled={loading}
                onChange={e => setName(e.target.value)}
              />

              <fieldset className="flex flex-col gap-2">
                <legend className="text-14 font-medium text-muted">
                  성별
                </legend>

                <div className="flex gap-2">
                  <Button
                    variant={
                      gender === 'MALE' ? 'primary' : 'secondary'
                    }
                    className="flex-1"
                    disabled={loading}
                    aria-pressed={gender === 'MALE'}
                    onClick={() => setGender('MALE')}
                  >
                    남성
                  </Button>

                  <Button
                    variant={
                      gender === 'FEMALE' ? 'primary' : 'secondary'
                    }
                    className="flex-1"
                    disabled={loading}
                    aria-pressed={gender === 'FEMALE'}
                    onClick={() => setGender('FEMALE')}
                  >
                    여성
                  </Button>
                </div>
              </fieldset>

              <Field
                label="생년월일"
                type="date"
                value={birthDate}
                disabled={loading}
                onChange={e => setBirthDate(e.target.value)}
              />

              <Field
                label="휴대폰 번호"
                type="tel"
                autoComplete="tel"
                placeholder="010-1234-5678"
                value={phoneNumber}
                disabled={loading}
                onChange={e => setPhoneNumber(e.target.value)}
              />


            </>
          )}

          {error && (
            <p role="alert" className="text-14 text-danger">
              {error}
            </p>
          )}

          {message && (
            <p role="status" className="text-14 text-brand">
              {message}
            </p>
          )}

        </div>

        <div className="hidden flex-col gap-2 lg:flex">
          {renderButtons()}
        </div>
      </form>
    </AppShell>
  );
}
