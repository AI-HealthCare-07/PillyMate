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

      const today = new Date();
      const limit = new Date(
        today.getFullYear() - 14,
        today.getMonth(),
        today.getDate()
      );

      const birthday = new Date(birthDate + 'T00:00:00');

      if (birthday >= limit) {
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
    setIsSignup(!isSignup);
    setError('');
    setMessage('');
    setPassword('');
  }

  // 5. 로그인 및 회원가입 요청
  function handleSubmit(event) {
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

    fetch(`${API_URL}/${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(requestData),
    })
      .then(function (response) {
        return response.json()
          .catch(function () {
            throw new Error('서버 응답을 확인할 수 없습니다.');
          })
          .then(function (data) {
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

            return data;
          });
      })
      .then(function (data) {
        if (isSignup) {
          // 회원가입 성공
          setIsSignup(false);
          setPassword('');
          setMessage('회원가입이 완료되었습니다. 로그인해 주세요.');
        } else {
          // 로그인 성공
          if (!data.access_token) {
            throw new Error('로그인 토큰을 받지 못했습니다.');
          }

          sessionStorage.setItem(
            'access_token',
            data.access_token
          );

          // 기존 자녀 관리 화면 이동
          go('children');
        }
      })
      .catch(function (err) {
        setError(
          err instanceof TypeError
            ? '서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.'
            : err.message
        );
      })
      .finally(function () {
        setLoading(false);
      });
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
